import pandas as pd

from models import AirlineStats

DATA_PATH = "data/flights.csv"


class FlightRepository:
    def __init__(self):
        self.df = pd.read_csv(DATA_PATH)

    def airports(self):
        airports = set(self.df["Origin_Airport"]) | set(self.df["Destination_Airport"])
        return sorted(airports)

    def overview(self):
        return {
            "total_flights": len(self.df),
            "avg_arrival_delay": round(self.df["Arrival_Delay_Min"].mean(), 1),
            "cancel_rate": round(self.df["Cancellation_Flag"].mean() * 100, 2),
            "total_profit": round(self.df["Profit_USD"].sum() / 1e9, 2),
        }

    def airline_stats(self):
        result = []
        for airline, group in self.df.groupby("Airline"):
            stats = AirlineStats(
                airline,
                len(group),
                round(group["Departure_Delay_Min"].mean(), 1),
                round(group["Arrival_Delay_Min"].mean(), 1),
                round(group["Cancellation_Flag"].mean() * 100, 2),
                round(group["Profit_USD"].mean()),
                round(group["Customer_Satisfaction"].mean(), 2),
            )
            result.append(stats)
        return result

    def delay_by_weather(self):
        mean_delay = self.df.groupby("Weather_Condition")["Arrival_Delay_Min"].mean()
        return mean_delay.round(1).sort_values(ascending=False).to_dict()

    def delay_by_reason(self):
        return self.df["Delay_Reason"].value_counts().to_dict()

    def route_data(self, origin, destination):
        is_origin = self.df["Origin_Airport"] == origin
        is_destination = self.df["Destination_Airport"] == destination
        return self.df[is_origin & is_destination]