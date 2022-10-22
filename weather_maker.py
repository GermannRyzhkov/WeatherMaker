#!/usr/bin/env python3

import os
import requests
import argparse
import cv2 as cv
from database_init import Forecast
from collections import defaultdict
from datetime import date, timedelta
from bs4 import BeautifulSoup

WEATHER_TYPES = ('Cloudy', 'Rainy', 'Snowy', 'Sunny')

WEATHER_CONDITION_DICT = {
    ('Cloud', 'cloud', 'overcast', 'Overcast', 'foggy', 'Foggy'): WEATHER_TYPES[0],
    ('Rain', 'rain', 'Drizzle', 'drizzle'): WEATHER_TYPES[1],
    ('Snow', 'snow'): WEATHER_TYPES[2],
    ('Sun', 'sun', 'Clear', 'clear'): WEATHER_TYPES[3]
}

WEATHER_COLOR_CODES = {
    WEATHER_TYPES[0]: (128, 128, 128),
    WEATHER_TYPES[1]: (255, 0, 0),
    WEATHER_TYPES[2]: (255, 191, 0),
    WEATHER_TYPES[3]: (0, 255, 255)
}


class ImageMaker:
    """Provide methods to create postcard with forecast info on it"""

    def __init__(self):
        self.weather_forecast = None
        self.dirname = os.path.dirname(__file__)
        self.template_path = os.path.join(self.dirname, 'python_snippets/external_data/probe.jpg')
        self.weather_img_path = os.path.join(self.dirname, 'python_snippets/external_data/weather_img')
        self.image = cv.imread(self.template_path)
        self.image = cv.resize(self.image, None, fx=1.5, fy=1)
        self.image_shape = self.image.shape

    def prepare_forecast(self, selected_date):
        """Parse selected date forecast from web."""
        weather_maker = WeatherMaker(start_date=selected_date, end_date=selected_date)
        selected_forecast = weather_maker.save_forecast()
        self.weather_forecast = selected_forecast[date.fromisoformat(selected_date)]
        return

    def make_postcard(self, selected_date):
        """Unite all other methods to prepare final version of postcard. Stores it in self.image."""
        self.prepare_forecast(selected_date)
        self.add_gradient()
        font = cv.FONT_HERSHEY_SIMPLEX
        x, y, delta = 20, 30, 50
        for key, value in self.weather_forecast.items():
            cv.putText(self.image, f'{key}: {value}', (x, y), font, 1, (0, 0, 0), 2, cv.LINE_AA)
            y += delta
        self.add_image()

    def add_gradient(self):
        """Adds gradient to postcard which color depends on type of weather"""
        initial_color = WEATHER_COLOR_CODES[self.weather_forecast['Weather condition']]
        coefficient_b = (255 - initial_color[0]) / self.image_shape[1]
        coefficient_g = (255 - initial_color[1]) / self.image_shape[1]
        coefficient_r = (255 - initial_color[2]) / self.image_shape[1]
        for x in range(self.image_shape[1]):
            b = initial_color[0] + x * coefficient_b
            g = initial_color[1] + x * coefficient_g
            r = initial_color[2] + x * coefficient_r
            cv.line(self.image, (x, 0), (x, self.image_shape[0]), (b, g, r))

    def add_image(self):
        """Adds small icon in bottom right corner of postcard. It indicates type of weather."""
        for dirpath, dirname, filenames in os.walk(self.weather_img_path):
            for file in filenames:
                if file.rstrip('.jpg') in self.weather_forecast['Weather condition'].lower():
                    file_path = os.path.join(self.weather_img_path, file)
                    weather_image = cv.imread(file_path)
                    y_range = (self.image_shape[0] - weather_image.shape[0], self.image_shape[0])
                    x_range = (self.image_shape[1] - weather_image.shape[1], self.image_shape[1])
                    self.image[y_range[0]:y_range[1], x_range[0]:x_range[1]] = weather_image
                    return

    def view_image(self, args):
        """Allows to view postcard with forecast information on it

        :param args: Namespace object with arguments selected_date and name_of_window
        """
        self.make_postcard(args.selected_date)
        cv.namedWindow(args.name_of_window, cv.WINDOW_NORMAL)
        cv.imshow(args.name_of_window, self.image)
        cv.waitKey(0)
        cv.destroyAllWindows()


class WeatherMaker:
    """
    Main class that implements few methods for parsing information from web and saving it to dictionary

    :param start_date: Date from which info parsing should start
    :param end_date: Date till which info parsing will be executed
    """

    def __init__(self, start_date, end_date):
        self.weather_forecast = defaultdict()
        self.start_date = date.fromisoformat(start_date)
        self.end_date = date.fromisoformat(end_date)

    def parse_temperature(self, soup):
        temperature = soup.find('div', {'class': 'temperature'})
        temperature = temperature.find('span', {'class': 'val swap'})
        temperature = temperature.get_text(separator=' ', strip=True)
        temperature = temperature[:-1] + 'deg C'
        return temperature

    def parse_weather_condition(self, soup):
        weather_condition = soup.find('p', id='summary')
        for condition_tuple in WEATHER_CONDITION_DICT.keys():
            for condition in condition_tuple:
                if condition in weather_condition.text:
                    return WEATHER_CONDITION_DICT[condition_tuple]
        else:
            return weather_condition.text

    def parse_wind(self, soup):
        wind = soup.find('div', {'class': 'wind'})
        wind = wind.find('span', {'class': 'val swap'})
        wind_force = wind.find('span', {'class': 'num swip'})
        wind_units = wind.find('span', {'class': 'unit swap'})
        wind_direction = wind.find('span', {'class': 'direction'})
        wind_direction = wind_direction['title']
        wind = f'{wind_force.text} {wind_units.text}    {wind_direction}'
        return wind

    def save_forecast(self):
        """Saves forecast to dictionary with structure dict[date.object] = dict(params).
        All parsing methods get "soup" attribute on invoke which represents Beautiful Soup object.
        """
        current_date = self.start_date
        while current_date <= self.end_date:
            url = f'https://darksky.net/details/46.9651,142.7393/{current_date}/si12/en'
            self.weather_forecast[current_date] = defaultdict()
            html_doc = requests.get(url)
            soup = BeautifulSoup(html_doc.text, features='html.parser')
            self.weather_forecast[current_date]['Date'] = current_date
            self.weather_forecast[current_date]['Temperature'] = self.parse_temperature(soup=soup)
            self.weather_forecast[current_date]['Weather condition'] = self.parse_weather_condition(soup=soup)
            self.weather_forecast[current_date]['Wind'] = self.parse_wind(soup=soup)
            current_date += timedelta(days=1)
        return self.weather_forecast


class DatabaseUpdater:
    """Class object that implements database interaction methods.

    :param database: Database instance
    """

    def __init__(self, database):
        self.database = database

    def get_forecast(self, args):
        """Retrieve forecast for selected dates from database and output it to console.

        :param args:  Namespace object with arguments start_date, end_date
        """
        start_date = date.fromisoformat(args.start_date)
        end_date = date.fromisoformat(args.end_date)
        selected_forecast = self.database.select().where(self.database.date.between(start_date, end_date)).order_by\
            (self.database.date)
        # print('Forecast for selected dates range:\n')
        for forecast in selected_forecast:
            print(
                f'Date: {forecast.date.isoformat()}     '
                f'Temperature: {forecast.temperature}   '
                f'Weather condition: {forecast.condition}   '
                f'Wind: {forecast.wind}'
            )
        return selected_forecast

    def store_forecast(self, args):
        """Parse forecast for selected dates from web and writes it to database.
        If record for specified date already exists -> overwrites information, otherwise creates new row

        :param args: Namespace object with arguments start_date, end_date
        """
        forecast = WeatherMaker(args.start_date, args.end_date).save_forecast()
        for record in forecast.values():
            data, created = self.database.get_or_create(
                date=record['Date'],
                defaults={
                    'temperature': record['Temperature'],
                    'condition': record['Weather condition'],
                    'wind': record['Wind']
                }
            )
            if created:
                query = self.database.update(
                    {
                        self.database.temperature: record['Temperature'],
                        self.database.condition: record['Weather condition'],
                        self.database.wind: record['Wind']
                    }
                ).where(self.database.date == record['Date'])
                query.execute()


def initial_launch(database):
    """
    This function is executed once main script was run.
    Collects last 7 days forecast from web, writes it to database, then output to console.
    """
    end_date = date.isoformat(date.today())
    start_date = date.isoformat(date.today() - timedelta(days=7))
    initial_args = argparse.Namespace(start_date=start_date, end_date=end_date)
    print('Last 7 days forecast is below:')
    database.store_forecast(initial_args)
    database.get_forecast(initial_args)
    print(3 * '\n')


if __name__ == '__main__':
    Forecast.create_table()
    db_upd = DatabaseUpdater(Forecast)
    img_maker = ImageMaker()
    initial_launch(db_upd)

    """Create main parser and subparsers list to reflect implemented functions"""
    parser = argparse.ArgumentParser(prog='Weather Maker',
                                     usage="You can call:\n"
                                           "1. 'store forecast' to collect forecast and write it to database. "
                                           "Necessary arguments are 'start date' 'end date' in format YYYY-MM-DD\n"
                                           "2. 'get forecast' to retrieve forecast from database and print it"
                                           "Necessary arguments are 'start date' 'end date' in format YYYY-MM-DD\n"
                                           "3. 'make image' to make postcard with forecast on selected day"
                                           "Necessary arguments are 'selected date' in format YYYY-MM-DD and "
                                           "'name of window'\n",
                                     description='Get weather forecast from web and stores it in database')
    subparsers = parser.add_subparsers(description='List of available commands')

    """Create subparser for forecast writing to database"""
    store_forecast = subparsers.add_parser('store forecast')
    store_forecast.add_argument('start_date', type=str, help='Date from which forecast to be selected')
    store_forecast.add_argument('end_date', type=str, help='Date until which forecast to be selected')
    store_forecast.set_defaults(func=db_upd.store_forecast)

    """Create subparser for forecast retrieve from database"""
    get_forecast = subparsers.add_parser('get forecast')
    get_forecast.add_argument('start_date', type=str, help='Date from which forecast to be selected')
    get_forecast.add_argument('end_date', type=str, help='Date until which forecast to be selected')
    get_forecast.set_defaults(func=db_upd.get_forecast)

    """Create subparser for making postcard with forecast information"""
    make_image = subparsers.add_parser('make image')
    make_image.add_argument('selected_date', type=str, help="Forecast's selected date")
    make_image.add_argument('name_of_window', type=str, help='Simply name of the window')
    make_image.set_defaults(func=img_maker.view_image)

    args = parser.parse_args(['store forecast', '2021-06-01', '2021-07-01'])
    args.func(args)
    args = parser.parse_args(['get forecast', '2021-06-20', '2021-07-04'])
    args.func(args)
    args = parser.parse_args(['make image', '2021-06-01', 'Postcard'])
    args.func(args)
