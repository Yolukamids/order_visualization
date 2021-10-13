"""
api - API 接口

Author: Hao
Date: 2021/9/10
"""
import random

import pymysql
from flask import Blueprint, request

from utils import get_mysql_connection, check_login

bp = Blueprint('api', __name__, url_prefix='/api')


@bp.route('/general_data')
@check_login
def get_general_data():
    names = ('GMV', '销售额', '实际销售额', '客单价')
    divsors = (10000, 10000, 10000, 1)
    units = ('万元', '万元', '万元', '元')
    values = [0] * 4
    conn = get_mysql_connection(database='data_viz')
    try:
        sql_queries = [
            'select sum(orderAmount) from tb_order',
            'select sum(payment) from tb_order',
            'select sum(payment) from tb_order where chargeback="否"',
            'select sum(payment) / count(distinct userID) from tb_order where chargeback="否"'
        ]
        with conn.cursor() as cursor:
            for i, query in enumerate(sql_queries):
                cursor.execute(query)
                values[i] = round(float(cursor.fetchone()[0]) / divsors[i], 2)
    except pymysql.MySQLError as err:
        print(err)
    finally:
        conn.close()
    results = [{'name': names[i], 'unit': units[i], 'value': values[i]} for i in range(4)]
    return {'results': results}


@bp.route('/gmv_by_month')
@check_login
def get_gmv_by_month():
    conn = get_mysql_connection(database='data_viz')
    months, gmvs = [], []
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('select month(orderTime) as month, sum(orderAmount) as gmv from tb_order group by month')
            row_dict = cursor.fetchone()
            while row_dict:
                months.append(f'{row_dict["month"]}月')
                gmvs.append(round(float(row_dict['gmv']) / 10000, 2))
                row_dict = cursor.fetchone()
    except pymysql.MySQLError as err:
        print(err)
    finally:
        conn.close()
    return {'x': months, 'y': gmvs}


@bp.route('/channel_data')
@check_login
def get_channel_data():
    conn = get_mysql_connection(database='data_viz')
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('select chanelID as name, count(distinct userID) as value from tb_order group by chanelID order by value desc')
            results = cursor.fetchall()
    except pymysql.MySQLError as err:
        print(err)
    finally:
        conn.close()
    return {'results': results}


@bp.route('/sales_data')
@check_login
def get_sales_data():
    y1_data = [random.randrange(10, 41) for _ in range(6)]
    y2_data = [random.randrange(20, 51) for _ in range(6)]
    y3_data = [random.randrange(30, 41) for _ in range(6)]
    y4_data = [random.randrange(20, 31) for _ in range(6)]
    return {'y1': y1_data, 'y2': y2_data, 'y3': y3_data, 'y4': y4_data}


@bp.route('/stock_data')
@check_login
def get_stock_data():
    page = int(request.args.get('page', 1))
    size = int(request.args.get('size', 10))
    start = request.args.get('start', '2020-1-1')
    end = request.args.get('end', '2020-12-31')
    conn = get_mysql_connection(database='stock')
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute(
                'select trade_date, open_price, close_price, low_price, high_price, trade_volume '
                'from tb_baba_stock where trade_date between %s and %s limit %s offset %s',
                (start, end, size, (page - 1) * size)
            )
            results = [{
                'date': row['trade_date'].strftime('%Y-%m-%d'),
                'open': f'{float(row["open_price"]):.2f}',
                'close': f'{float(row["close_price"]):.2f}',
                'low': f'{float(row["low_price"]):.2f}',
                'high': f'{float(row["high_price"]):.2f}',
                'volume':  row['trade_volume']
            } for row in cursor.fetchall()]
            cursor.execute(
                'select count(*) as total from tb_baba_stock where trade_date between %s and %s',
                (start, end)
            )
            total = cursor.fetchone()['total']
    finally:
        conn.close()
    return {'results': results, 'total_page': (total - 1) // size + 1}
