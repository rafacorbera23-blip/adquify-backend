
import pandas as pd

file_path = r"C:\Treball\1.Negocios\Adquify\GPAContract\Proveedores\Proveedores(Hoja1).csv"

# Try encodings
encodings = ['utf-8', 'latin-1', 'cp1252']
df = None

for enc in encodings:
    try:
        print(f"Trying encoding: {enc}")
        df = pd.read_csv(file_path, encoding=enc, sep=';')
        print("Success!")
        break
    except Exception as e:
        print(f"Failed with {enc}: {e}")

if df is not None:
    print("\nColumns:")
    print(df.columns.tolist())
    print("\nFirst 3 rows:")
    print(df.head(3).to_string())
else:
    print("Could not read file with common encodings.")
