# import sqlite3 as sq
import os

import pandas as pd
from sqlalchemy import MetaData, create_engine, inspect


class DataBaseInteractions:
    """This class provides functionality to read and write data from
    sqlite databases.
    """

    def __init__(self, path_to_database: str) -> None:
        """

        Args:
            path_to_database (str): Is the path to the database file.It must end with .db
        """
        self.path_to_database = r"sqlite:///" + path_to_database

    def write_to_database(self, data_frame: pd.DataFrame, table_name: str):
        """Writes data frame to an sqlite3 database. If the database does not exist it creates it.

        Args:
            data_frame (pd.DataFrame): _description_
            table_name (str): _description_
        """
        engine = create_engine(self.path_to_database)

        data_frame.to_sql(table_name, engine)

    def read_database(self, table_name: str) -> pd.DataFrame:
        engine = create_engine(self.path_to_database)
        data_frame = pd.read_sql(table_name, engine)
        return data_frame

    def get_all_table_names(self):
        engine = create_engine(self.path_to_database)
        inspect_object = inspect(engine)
        table_name_list = inspect_object.get_table_names()

        return table_name_list


if __name__ == "__main__":
    cwd = os.getcwd()
    print("cwd:", cwd)
    path_to_data_frame = os.path.join(
        "example", "Blast_furnace_route", "3stream_plan.xlsx"
    )
    path_to_database = os.path.join("example", "Blast_furnace_route", "test_db3.db")
    database_interactions = DataBaseInteractions(path_to_database)
    df = pd.read_excel(path_to_data_frame)
    print(df)

    database_interactions.write_to_database(df, "test_entry")
    a = database_interactions.read_database("test_entry")

    list_of_tables = database_interactions.get_all_table_names()
    print(list_of_tables)
