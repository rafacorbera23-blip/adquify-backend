import pandas as pd
import numpy as np
import re

# --- CONFIGURACIÓN DE ESTRATEGIA DE PRECIOS (ADQUIFY) ---
MULTIPLICADORES = {
    'General': 1.56,  # Margen estándar (Punt Moble Importació)
    'O': 1.02,        # Oferta (Punt Oferta AZUL)
    'Default': 1.60   # Margen de seguridad si no hay tipo definido
}

def limpiar_nombre(texto):
    """Convierte MAYÚSCULAS GRITONAS en Formato Título y añade branding"""
    if pd.isna(texto) or not texto: return "Producto Adquify Sin Nombre"
    texto = str(texto).title()
    # Eliminar palabras clave de proveedores si las hubiera
    texto = texto.replace("Mod.", "Serie").replace("Tap.", "Acabado")
    return texto

def calcular_pvp(row):
    """Calcula precio final basado en puntos (precio proveedor) y tipo"""
    # Mapping from internal JSON to user logic
    # 'price_supplier' is equivalent to 'Puntos'
    puntos = row.get('price_supplier', 0)
    
    # 'Tipo Punto' logic - currently defaulting to General as we don't have this field in raw data yet
    # Could be extended to map from 'source' or other fields
    tipo = row.get('type_point', 'General') 
    
    # Manejo de errores en datos
    if pd.isna(puntos) or points_is_empty(puntos): return 0.0
    
    # Seleccionar multiplicador
    factor = MULTIPLICADORES.get(tipo, MULTIPLICADORES['Default'])
    
    try:
        precio_final = float(puntos) * factor
        return round(precio_final, 2)
    except:
        return 0.0

def points_is_empty(puntos):
    return puntos == '' or puntos is None

class AdquifyProcessor:
    def __init__(self, products_list):
        """
        Initialize with a list of dictionaries (the internal catalog)
        """
        self.df = pd.DataFrame(products_list)
        
    def process(self):
        """
        Apply Adquify logic to the dataframe
        """
        if self.df.empty:
            return pd.DataFrame()

        # Ensure minimal columns exist
        if 'name_original' not in self.df.columns:
            self.df['name_original'] = self.df.get('name', 'Sin Nombre')
        if 'price_supplier' not in self.df.columns:
            self.df['price_supplier'] = 0.0

        print(f"🔄 Processing {len(self.df)} items with Adquify Protocol...")

        # 1. Limpiar Nombre
        self.df['Nombre_Comercial'] = self.df['name_original'].apply(limpiar_nombre)

        # 2. Generar/Usar SKU
        # We prefer the existing 'sku_adquify' if it exists, otherwise we generate a fallback
        if 'sku_adquify' in self.df.columns:
            self.df['SKU_Adquify'] = self.df['sku_adquify']
        else:
            # Fallback to user's logic if needed (though our scrapers should provide this)
            self.df['SKU_Adquify'] = self.df.apply(lambda row: f"ADQ-{str(row.get('id', 'UNKNOWN'))}", axis=1)

        # 3. Calcular PVP
        self.df['PVP_Adquify'] = self.df.apply(calcular_pvp, axis=1)

        # 4. Filter and Select Columns
        # Limpiar columnas irrelevantes para el cliente final
        # Map our internal columns to the output format expected
        self.df['Imagen'] = self.df['images'].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else (x if isinstance(x, str) else ''))
        
        # Dimensions (if available) - Create if not exist
        for col in ['Alto', 'Ancho', 'Fondo']:
            if col not in self.df.columns:
                self.df[col] = ''

        cols_finales = [
            'SKU_Adquify', 'Nombre_Comercial', 'PVP_Adquify', 
            'Alto', 'Ancho', 'Fondo', 'Imagen', 
            'product_url' # Keeping this for reference might be useful, user didn't ask but good to have, removal optional
        ]
        
        # Ensure all cols exist
        available_cols = [c for c in cols_finales if c in self.df.columns]
        
        catalogo_final = self.df[available_cols].copy()

        # Eliminar productos con precio 0 o errores
        catalogo_final = catalogo_final[catalogo_final['PVP_Adquify'] > 0]
        
        return catalogo_final
