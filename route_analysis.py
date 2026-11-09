from models import BinaryHeap, HashTable, RouteStats, lower_bound

DAY_NAMES = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
DAY_INDEX = {
    "Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3,
    "Friday": 4, "Saturday": 5, "Sunday": 6,
}


def by_avg_delay(item):
    return item["avg_delay"]


def format_time(minutes):
    """Минуты от начала недели -> 'Пн 08:15'."""
    day = DAY_NAMES[(minutes // 1440) % 7]
    hour = (minutes % 1440) // 60
    minute = minutes % 60
    return day + " " + str(hour).zfill(2) + ":" + str(minute).zfill(2)


def analyze_route(repo, origin, destination):
    if origin == destination:
        return None

    route = repo.route_data(origin, destination)
    if len(route) == 0:
        return None

    return RouteStats(origin,destination,
        len(route),
        round(route["Flight_Duration_Min"].mean()),         # Длительность полёта в минутах
        round(route["Departure_Delay_Min"].mean(), 1),      # Задержка вылета (в минутах)
        round(route["Arrival_Delay_Min"].mean(), 1),        # Задержка прилёта (в минутах)
        round(route["Cancellation_Flag"].mean() * 100, 2),  # Флаг отмены: 1 - отменён, 0 - состоялся. Переводим в %
        round(route["Profit_USD"].mean()),                  # Прибыль от рейса в долларах США
        round(route["Customer_Satisfaction"].mean(), 2),    # Оценка удовлетворённости клиентов (рейтинг)
    )


def rank_airlines(repo, origin, destination):
    """Авиакомпании на маршруте, сначала с наименьшей задержкой."""
    route = repo.route_data(origin, destination)
    result = []
    for airline, group in route.groupby("Airline"):
        result.append({
            "airline": airline,
            "flights": len(group),
            "avg_delay": round(group["Arrival_Delay_Min"].mean(), 1),
            "satisfaction": round(group["Customer_Satisfaction"].mean(), 2),
            "cancel_rate": round(group["Cancellation_Flag"].mean() * 100, 2),
        })
    result.sort(key=by_avg_delay)
    return result


def worst_routes(repo, top=5):
    """Маршруты с самой большой задержкой: достаём из кучи, а не сортируем."""
    df = repo.df
    df = df[df["Origin_Airport"] != df["Destination_Airport"]]

    heap = BinaryHeap()
    for (origin, destination), group in df.groupby(["Origin_Airport", "Destination_Airport"]):
        item = {
            "route": origin + " -> " + destination,
            "flights": len(group),
            "avg_delay": round(group["Arrival_Delay_Min"].mean(), 1),
        }
        heap.push(-item["avg_delay"], item)  # минус, чтобы наверху была максимальная задержка

    result = []
    while len(result) < top and not heap.is_empty():
        priority, item = heap.pop()
        result.append(item)
    return result


# ---------- граф рейсов с расписанием ----------

class Edge:
    """Все рейсы между двумя аэропортами."""

    def __init__(self, flights):
        flights.sort()
        self.flights = flights
        self.departures = []
        self.arrivals = []  # <--- Теперь храним как атрибут класса
        for i in range(len(flights)):
            self.departures.append(flights[i][0])
            self.arrivals.append((flights[i][1], i))

    def earliest_flight(self, ready_time):
        """Рейс, который прилетает раньше всех среди вылетающих не раньше ready_time."""
        i = lower_bound(self.departures, ready_time)  # бинарный поиск
        if i == len(self.departures):
            return None

        # Ищем минимальное время прилета в диапазоне от i до конца
        search_range = self.arrivals[i:]

        if not search_range:
            return None

        # min() по кортежу (время_прилёта, индекс) выберет нужный рейс.
        # Если время одинаковое, он выберет тот, у которого меньше индекс (что логично).
        arrival, index = min(search_range)

        return self.flights[index]


class FlightGraph:
    def __init__(self, repo, two_way=True):
        self.edges = HashTable()  # "FRA-CDG" -> Edge
        self.neighbours = HashTable()  # "FRA" -> ["CDG", "DEL", ...]
        self.two_way = two_way
        self.build(repo.df)

    def add_flight(self, groups, pairs, origin, destination, flight):
        key = origin + "-" + destination
        flights = groups.get(key)
        if flights is None:
            flights = []
            groups.put(key, flights)
            pairs.append((origin, destination))
        flights.append(flight)

    def build(self, df):
        df = df[(df["Cancellation_Flag"] == 0) & (df["Origin_Airport"] != df["Destination_Airport"])]
        groups = HashTable()
        pairs = []
        for row in df.itertuples():
            # в датасете нет времени вылета: день берём из Day_of_Week,
            # минуту суток из номера рейса
            departure = DAY_INDEX[row.Day_of_Week] * 1440 + row.Flight_Number % 1440
            arrival = departure + row.Flight_Duration_Min
            flight = (departure, arrival, row.Flight_ID, row.Airline)
            self.add_flight(groups, pairs, row.Origin_Airport, row.Destination_Airport, flight)

            # в датасете нет рейсов из аэропортов прилёта, поэтому
            # считаем, что у каждого рейса есть обратный с тем же расписанием
            if self.two_way:
                back = (departure, arrival, row.Flight_ID + "-обр", row.Airline)
                self.add_flight(groups, pairs, row.Destination_Airport, row.Origin_Airport, back)

        for origin, destination in pairs:
            key = origin + "-" + destination
            self.edges.put(key, Edge(groups.get(key)))
            if not self.neighbours.contains(origin):
                self.neighbours.put(origin, [])
            self.neighbours.get(origin).append(destination)

    def find_path(self, start, goal, start_time, min_layover=60):
        """Самый ранний прилёт из start в goal (алгоритм Дейкстры с расписанием)."""
        if start == goal:
            return None

        best = HashTable()  # аэропорт -> самое раннее время прилёта
        previous = HashTable()  # аэропорт -> (откуда, рейс)
        heap = BinaryHeap()
        best.put(start, start_time)
        heap.push(start_time, start)

        while not heap.is_empty():
            time, airport = heap.pop()
            if time > best.get(airport):
                continue
            if airport == goal:
                break

            if airport == start:
                ready = time
            else:
                ready = time + min_layover

            for destination in self.neighbours.get(airport, []):
                edge = self.edges.get(airport + "-" + destination)
                flight = edge.earliest_flight(ready)
                if flight is None:
                    continue
                arrival = flight[1]
                old = best.get(destination)
                if old is None or arrival < old:
                    best.put(destination, arrival)
                    previous.put(destination, (airport, flight))
                    heap.push(arrival, destination)

        if best.get(goal) is None:
            return None

        legs = []
        airport = goal
        while airport != start:
            prev_airport, flight = previous.get(airport)
            legs.append({
                "from": prev_airport,
                "to": airport,
                "flight_id": flight[2],
                "airline": flight[3],
                "departure": format_time(flight[0]),
                "arrival": format_time(flight[1]),
            })
            airport = prev_airport
        legs.reverse()

        total = best.get(goal) - start_time
        return {"legs": legs, "total_text": str(total // 60) + " ч " + str(total % 60) + " мин"}