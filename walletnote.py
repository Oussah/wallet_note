import streamlit as st
import datetime
import pymysql
from streamlit_option_menu import option_menu
import pandas as pd

# Database connection setup
def get_db_connection():
    try:
        # Connect to MySQL database
        connection = pymysql.connect(
            host='127.0.0.1',
            user='root',
            password='MySQLpassword1234',
            db='walletnote'  # Ensure this matches your database name
        )
        print("Database connection successful.")
        return connection
    except Exception as ex:
        print('PROBLEM WITH Database Connection:', ex)
        return None

# Expense Tracker class
class ExpenseTracker:
    def __init__(self):
        self.connection = get_db_connection()
        if self.connection:
            self.cursor = self.connection.cursor()
            self.create_table()
        else:
            raise ConnectionError("Failed to connect to the database.")

    def create_table(self):
        # The table name should be 'expenses', not 'walletnote'
        query = """
        CREATE TABLE IF NOT EXISTS expenses (
            date DATE NOT NULL,
            amount FLOAT NOT NULL,
            category VARCHAR(100),  # Adjusted length as per your schema
            description TEXT
        )
        """
        self.cursor.execute(query)
        self.connection.commit()

    def add_expense(self, date, amount, category, description=None):
        try:
            query = "INSERT INTO expenses (date, amount, category, description) VALUES (%s, %s, %s, %s)"
            self.cursor.execute(query, (date, amount, category, description))
            self.connection.commit()
            print("Expense added successfully.")
        except pymysql.MySQLError as e:
            print(f"Error adding expense: {e}")
            raise

    def get_expenses(self, start_date=None, end_date=None):
        query = "SELECT date, amount, category, description FROM expenses"
        if start_date and end_date:
            query += " WHERE date BETWEEN %s AND %s"
            self.cursor.execute(query, (start_date, end_date))
        else:
            self.cursor.execute(query)
        return self.cursor.fetchall()

    def calculate_total_expenditure(self, start_date=None, end_date=None):
        query = "SELECT SUM(amount) FROM expenses"
        if start_date and end_date:
            query += " WHERE date BETWEEN %s AND %s"
            self.cursor.execute(query, (start_date, end_date))
        else:
            self.cursor.execute(query)
        return self.cursor.fetchone()[0] or 0.0

    def delete_expense(self, date, amount, category, description=None):
        try:
            query = """
                DELETE FROM expenses
                WHERE date = %s AND amount = %s AND category = %s AND (description = %s OR description IS NULL)
            """
            self.cursor.execute(query, (date, amount, category, description))
            self.connection.commit()
            print("Expense deleted successfully.")
        except pymysql.MySQLError as e:
            print(f"Error deleting expense: {e}")
            raise

    def close_connection(self):
        if self.connection and self.connection.open:
            self.cursor.close()
            self.connection.close()

# Streamlit configuration
st.title("Welcome to Wallet Note")
st.markdown(
    '<h5 style="text-align: left;">Jot down your daily expenses with just multiple clicks!</h5>',
    unsafe_allow_html=True,
)

# Navigation Menu
selected = option_menu(
    menu_title=None,
    options=["Expenses Entry", "Expenses Overview", "Summary"],
    icons=["pencil-fill", "clipboard2-data", "bar-chart-fill"],
    orientation="horizontal",
)

expense_tracker = ExpenseTracker()

if selected == "Expenses Entry":
    st.header("Add Expenses")
    with st.expander("Add Expenses"):
        category = st.selectbox(
            "Category",
            (
                "Housing",
                "Food",
                "Transportation",
                "Entertainment",
                "School Tuition",
                "Medical",
                "Investment",
            ),
        )
        description = st.text_input("Description (optional)").title()
        value = st.number_input("Value", min_value=0.01)
        date = st.date_input("Date", value=datetime.date.today())

        if st.button("Add Expense"):
            try:
                expense_tracker.add_expense(date, value, category, description)
                st.success("Expense added successfully!")
            except pymysql.MySQLError as e:
                st.error(f"Error adding expense: {e}")

elif selected == "Expenses Overview":
    st.header("Expenses Overview")
    start_date = st.date_input("Start Date", value=datetime.date.today())
    end_date = st.date_input("End Date", value=datetime.date.today())

    if start_date > end_date:
        st.error("Start date cannot be after end date.")
    else:
        expenses = expense_tracker.get_expenses(start_date, end_date)
        if expenses:
            # Display expenses in a DataFrame
            df = pd.DataFrame(expenses, columns=["Date", "Amount", "Category", "Description"])
            st.write("### Expenses:")
            st.dataframe(df)

            # Add functionality to delete an expense
            st.write("### Delete an Expense")
            selected_index = st.number_input(
                "Select the row index to delete (0-based index from the table above)",
                min_value=0,
                max_value=len(df) - 1 if len(df) > 0 else 0,
                step=1,
            )

            if st.button("Delete Selected Expense"):
                selected_row = df.iloc[selected_index]
                try:
                    expense_tracker.delete_expense(
                        date=selected_row["Date"],
                        amount=selected_row["Amount"],
                        category=selected_row["Category"],
                        description=selected_row["Description"],
                    )
                    st.success("Expense deleted successfully!")
                    import time
                    time.sleep(1)
                    # Refresh the view
                    st.rerun()
                except Exception as e:
                    st.error(f"Error deleting expense: {e}")
        else:
            st.info("No expenses found in the selected date range.")

elif selected == "Summary":

    # Add buttons for choosing summary type
    summary_type = st.radio(
        "Select Summary View",
        options=["By Category", "By Month"],
        horizontal=True,
    )

    expenses = expense_tracker.get_expenses()
    if expenses:
        if summary_type == "By Category":
            # Create a dictionary to store total amounts by category
            category_totals = {}
            for date, amount, category, description in expenses:
                if category in category_totals:
                    category_totals[category] += amount
                else:
                    category_totals[category] = amount

            # Create a DataFrame for better visualization in Streamlit
            df = pd.DataFrame(list(category_totals.items()), columns=["Category", "Total Amount"])
            df = df.sort_values(by="Total Amount", ascending=False)

            st.write("### Expense Summary by Category")
            st.dataframe(df)  # Display the DataFrame as a table

        elif summary_type == "By Month":
            # Group expenses by month
            monthly_totals = {}
            for date, amount, category, description in expenses:
                month_year = date.strftime("%Y-%m")  # Format as 'YYYY-MM'
                if month_year in monthly_totals:
                    monthly_totals[month_year] += amount
                else:
                    monthly_totals[month_year] = amount

            # Create a DataFrame for monthly totals
            df = pd.DataFrame(list(monthly_totals.items()), columns=["Month", "Total Amount"])
            df = df.sort_values(by="Month")

            st.write("### Expense Summary by Month")
            st.dataframe(df)  # Display the DataFrame as a table
    else:
        st.info("No expenses recorded yet.")

# Ensure to close the connection at the end
expense_tracker.close_connection()
