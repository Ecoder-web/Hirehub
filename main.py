import os
import sys
import mysql.connector
import pandas as xy
import textwrap
import matplotlib.pyplot as plt
from collections import Counter



# ---------- CONFIG ----------

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "python",
    "database": "Hirehub"
}
TABLE_NAME = "hirehubdata_cleaned"



# ---- DB CONNECTION ----

try:
    mydb = mysql.connector.connect(**DB_CONFIG)
    cursor = mydb.cursor(dictionary=True)
    print("Connected to MySQL successfully")
except Exception as e:
    print("ERROR connecting to MySQL:", e)
    sys.exit(1)


# ---- UTIL / DISPLAY ----
def safe_columns_lower(df):
    df.columns = df.columns.str.lower()
    return df


def print_table_view(df):
    """Print a properly aligned plain table view of candidate data with truncated skills."""
    if df is None or df.empty:
        print("\nNo matching candidates found.")
        return

    df = safe_columns_lower(df.copy())

    columns = ["name", "college", "degree", "field", "company", "position", "skills"]
    header = [col.capitalize() for col in columns]

    max_widths = {
        "name": 15,
        "college": 20,
        "degree": 15,
        "field": 15,
        "company": 20,
        "position": 15,
        "skills": 50,
    }

    # Prepare rows with truncated text
    rows_truncated = []
    for _, row in df.iterrows():
        truncated_cells = []
        for col in columns:
            text = str(row.get(col, ""))
            width = max_widths.get(col, 20)
            if len(text) > width:
                truncated_text = text[:width-3] + "..."
            else:
                truncated_text = text
            truncated_cells.append(truncated_text)
        rows_truncated.append(truncated_cells)

    def line_sep(sep_char="-", joint_char="+"):
        parts = [sep_char * max_widths[col] for col in columns]
        return joint_char + joint_char.join(parts) + joint_char

    # Print header
    print()
    print(line_sep("=", "+"))
    header_line = "|"
    for col in columns:
        header_line += header[columns.index(col)].center(max_widths[col]) + "|"
    print(header_line)
    print(line_sep("=", "+"))

    # Print rows
    for row in rows_truncated:
        row_line = "|"
        for col_idx, cell_text in enumerate(row):
            width = max_widths[columns[col_idx]]
            row_line += cell_text.ljust(width) + "|"
        print(row_line)
        print(line_sep("-", "+"))
    print()



def card_view(df):
    """Print each candidate in the detailed card view."""
    if df is None or df.empty:
        print("\nNo matching candidates found.")
        return

    df = safe_columns_lower(df.copy())
    for idx, row in df.iterrows():
        print("-" * 60)
        print(f"Candidate #{idx + 1}")
        print("-" * 60)
        print(f"Name     : {row.get('name','')}")
        print(f"College  : {row.get('college','')}")
        print(f"Degree   : {row.get('degree','')}")
        print(f"Field    : {row.get('field','')}")
        print(f"Company  : {row.get('company','')}")
        print(f"Position : {row.get('position','')}")
        print("\nSkills:")
        skills_text = row.get('skills', '')
        for line in textwrap.wrap(str(skills_text), 80):
            print("  " + line)
        print("-" * 60 + "\n")

# TO CHOOSE B/W TABLE OR DETAILED VIEW
def choose_view_and_display(df):
    while True:
        choice = input("Choose view type: (1) Table view (2) Detailed view: ").strip()
        if choice == "1":
            print_table_view(df)
            break
        elif choice == "2":
            card_view(df)
            break
        else:
            print("Invalid choice. Please enter 1 or 2.")


# DATA BASE AND SEARCHING STUFF 

def fetch_all(): #------------ALL THE RAW DATA
    q = f"SELECT * FROM {TABLE_NAME}"
    cursor.execute(q)
    result = cursor.fetchall()
    return xy.DataFrame(result)


def fetch_filtered(field=None, college=None, degree=None, skills=None, company=None, position=None):#----FILTERING FUNCTION
    base = f"SELECT name, skills, college, degree, field, company, position FROM {TABLE_NAME}"
    filters = []
    if field:
        filters.append(parse_multi_input(field, "field"))
    if college:
        filters.append(parse_multi_input(college, "college"))
    if degree:
        filters.append(parse_multi_input(degree, "degree"))
    if company:
        filters.append(parse_multi_input(company, "company"))
    if position:
        filters.append(parse_multi_input(position, "position"))
    if skills:
        skill_filters = " AND ".join([f"skills LIKE '%{s}%'" for s in skills])
        filters.append(f"({skill_filters})")
    if filters:
        base += " WHERE " + " AND ".join(filters)
    cursor.execute(base)
    rows = cursor.fetchall()
    return xy.DataFrame(rows)


def add_candidate_db(data: dict): 
    q = f"INSERT INTO {TABLE_NAME} (name, skills, college, degree, field, company, position) VALUES (%s,%s,%s,%s,%s,%s,%s)"
    vals = (
        data.get("name"),
        data.get("skills"),
        data.get("college"),
        data.get("degree"),
        data.get("field"),
        data.get("company"),
        data.get("position"),
    )
    cursor.execute(q, vals)
    mydb.commit()


def update_candidate_db(column: str, new_value: str, name_search: str):
    q = f"UPDATE {TABLE_NAME} SET {column} = %s WHERE name LIKE %s"
    cursor.execute(q, (new_value, f"%{name_search}%"))
    mydb.commit()


def delete_candidate_db(name_search: str):
    cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE name LIKE %s", (f"%{name_search}%",))
    rows = cursor.fetchall()
    if not rows:
        print("No candidate found to delete.")
        return False
    df = xy.DataFrame(rows)
    choose_view_and_display(df)
    while True:
        agree = input("Type 'DELETE' to confirm deletion, or 'B' to go back without deleting: ").strip().upper()
        if agree == "DELETE":
            cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE name LIKE %s", (f"%{name_search}%",))
            mydb.commit()
            print("Deleted.")
            return True
        elif agree == "B":
            print("Delete cancelled.")
            return False
        else:
            print("Invalid input. Please type 'DELETE' to confirm or 'B' to cancel.")


def parse_multi_input(value, column_name):
    if not value:
        return None
    parts = [v.strip() for v in value.split(",") if v.strip()]
    if len(parts) == 1:
        return f"{column_name} LIKE '%{parts[0]}%'"
    or_conditions = " OR ".join([f"{column_name} LIKE '%{v}%'" for v in parts])
    return f"({or_conditions})"

# EXPORT, SORT, VISUALISATION

def export_df(df, name_prefix="hirehub_export"): #--------------------------EXPORT
    if df is None or df.empty:
        print("Nothing to export.")
        return
    csv_file = f"{name_prefix}.csv"
    xlsx_file = f"{name_prefix}.xlsx"
    try:
        df.to_csv(csv_file, index=False, encoding="utf-8")
        print(f"Saved CSV -> {csv_file}")
    except Exception:
        print("Failed to save CSV")
    try:
        df.to_excel(xlsx_file, index=False)
        print(f"Saved Excel -> {xlsx_file}")
    except Exception:
        pass


def sort_dataframe(df): #---------------------ALL UNIQUE SORRRTS ----------------------------
    if df is None or df.empty:
        print("No data to sort.")
        return df
    df = safe_columns_lower(df.copy())
    print("\nSort options:")
    options = [
        ("name", "Name (A→Z)"),
        ("college", "College (A→Z)"),
        ("degree", "Degree (A→Z)"),
        ("field", "Field (A→Z)"),
        ("company", "Company (A→Z)"),
        ("position", "Position (A→Z)"),
        ("skills_count", "Number of Skills (descending)"),
    ]
    for i, (_, label) in enumerate(options, 1):
        print(f"{i}. {label}")
    choice = input("Choose sort option (number): ").strip()
    try:
        idx = int(choice) - 1
        key = options[idx][0]
    except Exception:
        print("Invalid choice.")
        return df

    if key == "skills_count":
        df["skills_count"] = df["skills"].fillna("").apply(lambda s: len([x for x in str(s).split(",") if x.strip()]))
        df_sorted = df.sort_values(by="skills_count", ascending=False)
        df = df.drop(columns=["skills_count"])
    else:
        df_sorted = df.sort_values(by=key, ascending=True, na_position="last")
    return df_sorted


def stats_dashboard(df=None): # ------------------ DISPLAY OF GRAPHS
    try:
        if df is None or df.empty:
            df = fetch_all()
        if df.empty:
            print("No data available for statistics.")
            return

        df = safe_columns_lower(df.copy())

        colleges = df["college"].fillna("Unknown").astype(str)
        top_colleges = Counter([c.strip() for c in colleges if c.strip()])
        most_common_colleges = top_colleges.most_common(10)
        if most_common_colleges:
            labels, vals = zip(*most_common_colleges)
            plt.figure(figsize=(10, 5))
            plt.bar(range(len(vals)), vals, tick_label=labels)
            plt.xticks(rotation=45, ha="right")
            plt.title("Top 10 Colleges (by candidate count)")
            plt.tight_layout()
            plt.show()

        degrees = df["degree"].fillna("Unknown").astype(str)
        degree_counts = Counter([d.strip() for d in degrees if d.strip()])
        labels, vals = zip(*degree_counts.most_common(10))
        plt.figure(figsize=(8, 6))
        plt.pie(vals, labels=labels, autopct="%1.1f%%", startangle=140)
        plt.title("Degree distribution (top 10)")
        plt.tight_layout()
        plt.show()

        fields = df["field"].fillna("Unknown").astype(str)
        field_counts = Counter([f.strip() for f in fields if f.strip()])
        labels, vals = zip(*field_counts.most_common(10))
        plt.figure(figsize=(10, 5))
        plt.bar(range(len(vals)), vals, tick_label=labels)
        plt.xticks(rotation=45, ha="right")
        plt.title("Top 10 Fields of Study")
        plt.tight_layout()
        plt.show()

    except Exception:
        print("Failed to generate charts.")



# -------------------------------------------------------FINAL MENU
def candidate_management_menu():
    while True:
        print("\n" + "=" * 60)
        print(" CANDIDATE MANAGEMENT ".center(60))
        print("=" * 60)
        print("1. Add Candidate".center(60))
        print("2. Edit Candidate".center(60))
        print("3. Delete Candidate".center(60))
        print("4. Search Candidate (quick)".center(60))
        print("5. Back".center(60))
        print("=" * 60)
        choice = input("\nEnter choice: ").strip()
        if choice == "1":
            data = {}
            data["name"] = input("Enter Name: ").strip()
            data["skills"] = input("Enter Skills (comma-separated): ").strip()
            data["college"] = input("Enter College: ").strip()
            data["degree"] = input("Enter Degree: ").strip()
            data["field"] = input("Enter Field of Study: ").strip()
            data["company"] = input("Enter Current Company: ").strip()
            data["position"] = input("Enter Position: ").strip()
            add_candidate_db(data)
        elif choice == "2":
            name = input("Enter candidate name to edit (partial ok): ").strip()
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE name LIKE %s", (f"%{name}%",))
            rows = cursor.fetchall()
            if not rows:
                print("No matching records.")
                continue
            df = xy.DataFrame(rows)
            choose_view_and_display(df)
            col = input("Which column to update? (skills/college/degree/field/company/position): ").strip().lower()
            if col not in ["skills", "college", "degree", "field", "company", "position"]:
                print("Invalid column choice.")
                continue
            val = input(f"Enter new value for {col}: ").strip()
            update_candidate_db(col, val, name)
        elif choice == "3":
            name = input("Enter name (partial) to delete: ").strip()
            cursor.execute(f"SELECT * FROM {TABLE_NAME} WHERE name LIKE %s", (f"%{name}%",))
            rows = cursor.fetchall()
            if not rows:
                print("No candidate found to delete.")
                continue
            df = xy.DataFrame(rows)
            choose_view_and_display(df)
            while True:
                agree = input("Type 'DELETE' to confirm deletion, or 'B' to go back without deleting: ").strip().upper()
                if agree == "DELETE":
                    cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE name LIKE %s", (f"%{name}%",))
                    mydb.commit()
                    print("Deleted.")
                    break
                elif agree == "B":
                    print("Delete cancelled.")
                    break
                else:
                    print("Invalid input. Please type 'DELETE' to confirm or 'B' to cancel.")
        elif choice == "4":
            term = input("Search by name/skill/college (partial): ").strip()
            q = f"SELECT name, skills, college, degree, field, company, position FROM {TABLE_NAME} WHERE name LIKE %s OR skills LIKE %s OR college LIKE %s"
            like = f"%{term}%"
            cursor.execute(q, (like, like, like))
            rows = cursor.fetchall()
            df = xy.DataFrame(rows)
            choose_view_and_display(df)
        elif choice == "5":
            return
        else:
            print("Invalid choice")


def data_insights_menu():
    last_df = None
    while True:
        print("\n" + "=" * 60)
        print(" DATA & INSIGHTS ".center(60))
        print("=" * 60)
        print("1. Filter Candidates".center(60))
        print("2. Sort Candidates (works on last filtered / all)".center(60))
        print("3. Export (CSV / Excel)".center(60))
        print("4. View Stats Dashboard (Matplotlib)".center(60))
        print("5. Back".center(60))
        print("=" * 60)
        choice = input("\nEnter choice: ").strip()

        if choice == "1":
            print("\n(You can provide multiple values comma-separated)")
            field = input("Field(s) (or Enter to skip): ").strip() or None
            college = input("College(s) (or Enter to skip): ").strip() or None
            degree = input("Degree(s) (or Enter to skip): ").strip() or None
            company = input("Company(s) (or Enter to skip): ").strip() or None
            position = input("Position(s) (or Enter to skip): ").strip() or None
            skills_input = input("Skill(s) (comma separated, AND logic) (or Enter to skip): ").strip()
            skills = [s.strip() for s in skills_input.split(",")] if skills_input else None
            df = fetch_filtered(field, college, degree, skills, company, position)
            last_df = df
            choose_view_and_display(df)
        elif choice == "2":
            if last_df is None or last_df.empty:
                print("No filtered results in memory, using all data.")
                last_df = fetch_all()
            last_df = sort_dataframe(last_df)
            choose_view_and_display(last_df)
        elif choice == "3":
            if last_df is None or last_df.empty:
                print("No filtered results in memory, exporting entire dataset.")
                df_export = fetch_all()
            else:
                df_export = last_df
            export_df(df_export)
        elif choice == "4":
            if last_df is None or last_df.empty:
                df_stats = fetch_all()
            else:
                df_stats = last_df
            stats_dashboard(df_stats)
        elif choice == "5":
            return
        else:
            print("Invalid choice")


# ----------------------------------------------------STATRT END SEQUENCE

def main():
    while True:
        print("\n" + "=" * 70)
        print(" HIREHUB DATABASE - MAIN MENU ".center(70))
        print("=" * 70)
        print("1. Candidate Management".center(70))
        print("2. Data & Insights".center(70))
        print("3. Exit".center(70))
        print("=" * 70)
        choice = input("\nEnter choice (1-3): ").strip()
        if choice == "1":
            candidate_management_menu()
        elif choice == "2":
            data_insights_menu()
        elif choice == "3":
            print("Goodbye. Closing HireHub.")
            break
        else:
            print("Invalid choice")


#*************************************************************************CODE END
# ENTRY POINT 
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted. Exiting.")
    except Exception:
        print("Fatal error occurred.")
