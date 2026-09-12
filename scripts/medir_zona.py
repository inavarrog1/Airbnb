"""Mide el area real de un poligono de Portal Inmobiliario.

Decodifica el parametro polygon_location (polyline codificada) y calcula el
area con shoelace sobre una proyeccion plana local. El bounding box de la URL
sobreestima: en la zona confirmada, el poligono es el 19% de su caja.

Uso:  python3 scripts/medir_zona.py "<url>"
"""
import sys
import math, urllib.parse

URL_DEFAULT = "https://www.portalinmobiliario.com/venta/departamento/_DisplayType_M_item*location_lat:-33.43399063809945*-33.40676791096829,lon:-70.62473552398681*-70.57761447601318?polygon_location=n%7E%7CjEn%7CxmLgAjb%40L%7CZj%40xJ%60Gl%5BbBhZbBjKrF%60ObFbH%60GvQjDpFpKrHlL%60GnGhC%7CG%60%40rF_FZmEMo%5Cy%40cHyDuPsJ_U%7B%5D_k%40oG_NwEcOkH%7D%5B%7DCcHk%40%7DL%5Ba%40%7DC%3FyDfC%5BcA"

url = sys.argv[1] if len(sys.argv) > 1 else URL_DEFAULT

def decode(s):
    pts, i, lat, lng = [], 0, 0, 0
    while i < len(s):
        for which in (0, 1):
            shift = result = 0
            while True:
                b = ord(s[i]) - 63; i += 1
                result |= (b & 0x1f) << shift; shift += 5
                if b < 0x20: break
            d = ~(result >> 1) if result & 1 else (result >> 1)
            if which == 0: lat += d
            else: lng += d
        pts.append((lat * 1e-5, lng * 1e-5))
    return pts

enc = urllib.parse.unquote(url.split('polygon_location=')[1])
pts = decode(enc)
print("\nvertices del poligono:", len(pts))

lats = [p[0] for p in pts]; lons = [p[1] for p in pts]
print("lat  %.5f -> %.5f" % (min(lats), max(lats)))
print("lon  %.5f -> %.5f" % (min(lons), max(lons)))

# proyeccion local plana en metros
lat0 = sum(lats)/len(lats)
mlat = 111132.0
mlon = 111320.0 * math.cos(math.radians(lat0))
xy = [((lo - min(lons)) * mlon, (la - min(lats)) * mlat) for la, lo in pts]

# shoelace
a = 0.0
for i in range(len(xy)):
    x1, y1 = xy[i]; x2, y2 = xy[(i+1) % len(xy)]
    a += x1*y2 - x2*y1
area_poly = abs(a)/2/1e6

# bbox declarado en la URL
loc = url.split('location_lat:')[1].split('?')[0]
blat = sorted(float(v) for v in loc.split(',')[0].split('*'))
blon = sorted(float(v) for v in loc.split('lon:')[1].split('*'))
bbox = ((blat[1]-blat[0])*mlat/1000) * ((blon[1]-blon[0])*mlon/1000)

print("\nAREA DEL POLIGONO : %.2f km2" % area_poly)
print("area del bbox URL : %.2f km2" % bbox)
print("el poligono es el %.0f%% del bbox" % (100*area_poly/bbox))
print("\ncriterio del item 01 (area real < 3 km2): %s" % ("PASA" if area_poly < 3 else "NO PASA"))
print("estimacion de avisos a 528/km2: ~%d" % round(area_poly*528))
