
file_path = r"C:\Treball\1.Negocios\Adquify\GPAContract\Proveedores\Proveedores(Hoja1).csv"

with open(file_path, 'r', encoding='latin-1', errors='replace') as f:
    for i in range(10):
        print(repr(f.readline()))
