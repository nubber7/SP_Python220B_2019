"""
This program imports the data in the csv files linearly
"""

import logging
import csv
import os
import sys
from timeit import timeit as timer
import psutil
from pymongo import MongoClient
sys.path.append(os.path.join(os.path.dirname(__file__), 'csvs'))

LOG_FORMAT = "%(asctime)s %(filename)s:%(lineno)-3d %(levelname)s %(message)s"
LOG_FILE = 'parallel.log'
FORMATTER = logging.Formatter(LOG_FORMAT)
FILE_HANDLER = logging.FileHandler(LOG_FILE)
FILE_HANDLER.setLevel(logging.DEBUG)
FILE_HANDLER.setFormatter(FORMATTER)
logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)
LOGGER.addHandler(FILE_HANDLER)
LOGGER.setLevel(logging.DEBUG)

class MongoDBConnection():
    """MongoDB Connection"""
    def __init__(self, host='127.0.0.1', port=27017):
        """Initiates the connection settings"""
        self.host = host
        self.port = port
        self.connection = None

    def __enter__(self):
        """Connects to MongoDB"""
        self.connection = MongoClient(self.host, self.port)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Disconnects from MongoDB"""
        self.connection.close()

def main():
    """This method runs a timer and cpu usage tracker for the program"""
    time_taken = timer('import_data()', globals=globals(), number=1)
    cpu_usage = psutil.cpu_percent()
    LOGGER.debug("Linear program time: %s seconds", time_taken)
    LOGGER.debug("This program's cpu usage was: %s%%", cpu_usage)
    return time_taken, cpu_usage

def import_data(directory_name='csvs', product_file='product_data.csv',
                customer_file='customer_data.csv', rentals_file='rentals_data.csv'):
    """This function takes a directory name and three csv files and creates/populates a new
       MongoDB database with the data. It then returns two tuples: The first contains a record
       count of the number of products, customers and rentals added. The second contains a count
       of any errors that occurred in products, customers, and rentals"""

    count_dict = {}
    count_dict.setdefault('product_errors', 0)
    count_dict.setdefault('customer_errors', 0)
    count_dict.setdefault('rentals_errors', 0)
    count_dict.setdefault('product_count_before', 0)
    count_dict.setdefault('customer_count_before', 0)
    count_dict.setdefault('product_count_after', 0)
    count_dict.setdefault('customer_count_after', 0)
    count_dict.setdefault('product_time', 0)
    count_dict.setdefault('product_time', 0)
    count_dict.setdefault('customer_time', 0)

    count_dict = universal_import(directory_name, product_file, 'product_errors', count_dict)
    count_dict = universal_import(directory_name, customer_file, 'customer_errors', count_dict)
    universal_import(directory_name, rentals_file, 'rentals_errors', count_dict)

    product_tuple = (count_dict['product_count_after'] - count_dict['product_count_before'],
                     count_dict['product_count_before'], count_dict['product_count_after'],
                     count_dict['product_time'])
    customer_tuple = (count_dict['customer_count_after'] - count_dict['customer_count_before'],
                      count_dict['customer_count_before'], count_dict['customer_count_after'],
                      count_dict['customer_time'])
    LOGGER.debug("%s, %s", product_tuple, customer_tuple)
    return product_tuple, customer_tuple

def universal_import(directory_name, file, error_index, count_dict):
    """This method will import any of the .csv files"""
    LOGGER.debug("Importing %s", file)
    mongo = MongoDBConnection()
    with mongo:
        database = mongo.connection.rental_company
        try:
            if file == 'product_data.csv':
                for entry in database.product.find():
                    count_dict['product_count_before'] += len(entry)
                count_dict['product_time'] = timer('product_file_reader()',
                                                   globals=globals(), number=1)
                for entry in database.product.find():
                    count_dict['product_count_after'] += len(entry)
            elif file == 'customer_data.csv':
                for entry in database.customer.find():
                    count_dict['customer_count_before'] += len(entry)
                count_dict['customer_time'] = timer('customer_file_reader()',
                                                    globals=globals(), number=1)
                for entry in database.customer.find():
                    count_dict['customer_count_after'] += len(entry)
            elif file == 'rentals_data.csv':
                rentals_file_reader()
        except Exception as ex:
            count_dict[error_index] += 1
            LOGGER.warning(ex)
            LOGGER.warning("Something went wrong while reading file")
        LOGGER.debug("Successfully imported %s", file)

    return count_dict

def product_file_reader():
    """This method will loop through and read the product_file"""
    mongo = MongoDBConnection()
    with mongo:
        database = mongo.connection.rental_company
        product = database["product"]
        products_dict = {}
        try:
            with open(os.path.join(os.path.dirname(__file__), 'csvs', 'product_data.csv'),
                      newline='') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    products_dict[row['id']] = {'description': row['description'],
                                                'product_type': row['product_type'],
                                                'quantity_available': row['quantity_available']}
                product.insert_one(products_dict)
        except FileNotFoundError:
            LOGGER.error("Could not find product_data.csv")

def customer_file_reader():
    """This method will loop through and read the product_file"""
    mongo = MongoDBConnection()
    with mongo:
        database = mongo.connection.rental_company
        customer = database["customer"]
        customer_dict = {}
        try:
            with open(os.path.join(os.path.dirname(__file__), 'csvs', 'customer_data.csv'),
                      newline='') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    customer_dict[row['id']] = {'name': row['name'], 'address': row['address'],
                                                'phone_number': row['phone_number']}
                customer.insert_one(customer_dict)
        except FileNotFoundError:
            LOGGER.error("Could not find customer_data.csv")

def rentals_file_reader():
    """This method will loop through and read the product_file"""
    mongo = MongoDBConnection()
    with mongo:
        database = mongo.connection.rental_company
        rentals = database["rentals"]
        rentals_dict = {}
        try:
            with open(os.path.join(os.path.dirname(__file__), 'csvs', 'rentals_data.csv'),
                      newline='') as csv_file:
                reader = csv.DictReader(csv_file)
                for row in reader:
                    rentals_dict[row['id']] = {'name': row['name'],
                                               'rentals': row['rentals'].split()}
                rentals.insert_one(rentals_dict)
        except FileNotFoundError:
            LOGGER.error("Could not find rentals_data.csv")

def delete_database():
    """This method deletes the database to reset for other tests"""
    mongo = MongoDBConnection()
    with mongo:
        database = mongo.connection.rental_company
        database.product.drop()
        database.customer.drop()
        database.rentals.drop()
    LOGGER.debug("Cleared database")

if __name__ == '__main__':
    main()
