from fastapi import FastAPI, Query
from app.athena import run_query

app = FastAPI(title="PharmaTrack Analytics", version="1.0.0")

@app.get("/health")
def health():
    return {"ok": True}

@app.get("/kpi/fill-rate")
def kpi_fill_rate(desde: str = Query(...), hasta: str = Query(...)):
    sql = f"""
    WITH req AS (
      SELECT id_producto, SUM(cantidad_requerida) AS requerido
      FROM recetas_detalle
      WHERE fecha BETWEEN TIMESTAMP '{desde} 00:00:00' AND TIMESTAMP '{hasta} 23:59:59'
      GROUP BY 1
    ),
    disp AS (
      SELECT id_producto, SUM(cantidad_dispensada) AS dispensado
      FROM dispensaciones
      WHERE fecha BETWEEN TIMESTAMP '{desde} 00:00:00' AND TIMESTAMP '{hasta} 23:59:59'
      GROUP BY 1
    ),
    mix AS (
      SELECT COALESCE(r.id_producto,d.id_producto) AS id_producto,
             COALESCE(r.requerido,0) AS requerido,
             COALESCE(d.dispensado,0) AS dispensado
      FROM req r FULL OUTER JOIN disp d ON r.id_producto = d.id_producto
    )
    SELECT
      SUM(least(dispensado, requerido)) AS atendido_efectivo,
      SUM(requerido) AS demandado,
      CASE WHEN SUM(requerido)=0 THEN 1
           ELSE CAST(SUM(least(dispensado, requerido)) AS DOUBLE) / SUM(requerido) END AS fill_rate
    FROM mix;
    """
    rows = run_query(sql)
    r = rows[0] if rows else {}
    return {
      "desde": desde, "hasta": hasta,
      "atendido": float(r.get("atendido_efectivo", 0) or 0),
      "demandado": float(r.get("demandado", 0) or 0),
      "fill_rate": float(r.get("fill_rate", 0) or 0)
    }

@app.get("/kpi/stockout")
def kpi_stockout(desde: str = Query(...), hasta: str = Query(...)):
    sql = f"""
    WITH req AS (
      SELECT id_producto, id_sucursal, SUM(cantidad_requerida) AS requerido
      FROM recetas_detalle
      WHERE fecha BETWEEN TIMESTAMP '{desde} 00:00:00' AND TIMESTAMP '{hasta} 23:59:59'
      GROUP BY 1,2
    ),
    disp AS (
      SELECT id_producto, id_sucursal, SUM(cantidad_dispensada) AS dispensado
      FROM dispensaciones
      WHERE fecha BETWEEN TIMESTAMP '{desde} 00:00:00' AND TIMESTAMP '{hasta} 23:59:59'
      GROUP BY 1,2
    ),
    mix AS (
      SELECT COALESCE(r.id_producto,d.id_producto) AS id_producto,
             COALESCE(r.id_sucursal,d.id_sucursal) AS id_sucursal,
             COALESCE(r.requerido,0) AS req,
             COALESCE(d.dispensado,0) AS disp
      FROM req r FULL OUTER JOIN disp d
      ON r.id_producto=d.id_producto AND r.id_sucursal=d.id_sucursal
    )
    SELECT id_sucursal,
           COUNT_IF(req>0 AND disp=0) AS productos_en_stockout
    FROM mix
    GROUP BY 1
    ORDER BY productos_en_stockout DESC;
    """
    rows = run_query(sql)
    return {"desde": desde, "hasta": hasta, "rows": rows, "count": len(rows)}

@app.get("/top/quiebres")
def top_quiebres(desde: str = Query(...), hasta: str = Query(...), limit: int = 20):
    sql = f"""
    WITH req AS (
      SELECT id_producto, SUM(cantidad_requerida) AS req
      FROM recetas_detalle
      WHERE fecha BETWEEN TIMESTAMP '{desde} 00:00:00' AND TIMESTAMP '{hasta} 23:59:59'
      GROUP BY 1
    ),
    disp AS (
      SELECT id_producto, SUM(cantidad_dispensada) AS disp
      FROM dispensaciones
      WHERE fecha BETWEEN TIMESTAMP '{desde} 00:00:00' AND TIMESTAMP '{hasta} 23:59:59'
      GROUP BY 1
    ),
    mix AS (
      SELECT COALESCE(r.id_producto,d.id_producto) AS id_producto,
             COALESCE(r.req,0)  AS req,
             COALESCE(d.disp,0) AS disp
      FROM req r FULL OUTER JOIN disp d ON r.id_producto=d.id_producto
    )
    SELECT id_producto,
           req,
           disp,
           GREATEST(req - disp, 0) AS faltante
    FROM mix
    WHERE req > 0
    ORDER BY faltante DESC
    LIMIT {int(limit)};
    """
    rows = run_query(sql)
    return {"desde": desde, "hasta": hasta, "rows": rows, "count": len(rows)}
