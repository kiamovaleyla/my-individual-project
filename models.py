class AirlineStats:
    def __init__(self, airline, flights, dep_delay, arr_delay, cancel_rate, profit, satisfaction):
        self.airline = airline
        self.flights = flights
        self.dep_delay = dep_delay
        self.arr_delay = arr_delay
        self.cancel_rate = cancel_rate
        self.profit = profit
        self.satisfaction = satisfaction


class RouteStats:
    def __init__(self, origin, destination, flights, duration, dep_delay, arr_delay,
                 cancel_rate, profit, satisfaction):
        self.origin = origin
        self.destination = destination
        self.flights = flights
        self.duration = duration
        self.dep_delay = dep_delay
        self.arr_delay = arr_delay
        self.cancel_rate = cancel_rate
        self.profit = profit
        self.satisfaction = satisfaction


# бинарный поиск 

def lower_bound(items, value):
    """бинарный поиск левой границы, индекс первого элемента, который >= value (список отсортирован)."""
    left = 0
    right = len(items)
    while left < right:
        middle = (left + right) // 2
        if items[middle] < value:
            left = middle + 1
        else:
            right = middle
    return left




class HashTable:
    def __init__(self, size=16):
        self.size = size
        self.count = 0
        self.buckets = []
        for i in range(size):
            self.buckets.append([])

    def index(self, key):
        h = 0
        for ch in str(key):
            h = (h * 31 + ord(ch)) % self.size
        return h

    def put(self, key, value):
        bucket = self.buckets[self.index(key)]
        for pair in bucket:
            if pair[0] == key:
                pair[1] = value
                return
        bucket.append([key, value])
        self.count += 1
        if self.count > self.size * 0.75:
            self.grow()

    def get(self, key, default=None):
        bucket = self.buckets[self.index(key)]
        for pair in bucket:
            if pair[0] == key:
                return pair[1]
        return default

    def contains(self, key):
        bucket = self.buckets[self.index(key)]
        for pair in bucket:
            if pair[0] == key:
                return True
        return False

    def remove(self, key):
        bucket = self.buckets[self.index(key)]
        for i in range(len(bucket)):
            if bucket[i][0] == key:
                bucket.pop(i)
                self.count -= 1
                return True
        return False

    def keys(self):
        result = []
        for bucket in self.buckets:
            for pair in bucket:
                result.append(pair[0])
        return result

    def grow(self):
        old_buckets = self.buckets
        self.size = self.size * 2
        self.count = 0
        self.buckets = []
        for i in range(self.size):
            self.buckets.append([])
        for bucket in old_buckets:
            for pair in bucket:
                self.put(pair[0], pair[1])




class BinaryHeap:
    def __init__(self):
        self.data = []  # пары (приоритет, элемент)

    def is_empty(self):
        return len(self.data) == 0

    def push(self, priority, item):
        self.data.append((priority, item))
        self.sift_up(len(self.data) - 1)

    def pop(self):
        top = self.data[0]
        last = self.data.pop()
        if len(self.data) > 0:
            self.data[0] = last
            self.sift_down(0)
        return top

    def sift_up(self, i):
        while i > 0:
            parent = (i - 1) // 2
            if self.data[i][0] < self.data[parent][0]:
                self.data[i], self.data[parent] = self.data[parent], self.data[i]
                i = parent
            else:
                break

    def sift_down(self, i):
        n = len(self.data)
        while True:
            left = 2 * i + 1
            right = 2 * i + 2
            smallest = i
            if left < n and self.data[left][0] < self.data[smallest][0]:
                smallest = left
            if right < n and self.data[right][0] < self.data[smallest][0]:
                smallest = right
            if smallest == i:
                break
            self.data[i], self.data[smallest] = self.data[smallest], self.data[i]
            i = smallest
