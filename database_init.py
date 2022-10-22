import peewee
from playhouse.db_url import connect


class Forecast(peewee.Model):
    date = peewee.DateField()
    temperature = peewee.CharField()
    condition = peewee.CharField()
    wind = peewee.CharField()

    class Meta:
        database = connect('sqlite:///forecast.db')

