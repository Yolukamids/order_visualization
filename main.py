"""
main.py -

Author: Hao
Date: 2021/9/9
"""
import hashlib
from datetime import timedelta
import io

import flask
import openpyxl
import pymysql.cursors
from flask import redirect, session, request, make_response
from flask_cors import CORS

import captcha
from api import bp
from utils import random_captcha_code, check_login, get_mysql_connection

app = flask.Flask(__name__)
CORS(app)


# 注册蓝图
app.register_blueprint(bp)

app.secret_key = 'Tl8sTUsNSzIjbjQkYDxGdmVoRmxHIWw8'
app.permanent_session_lifetime = timedelta(days=7)


@app.route('/')
@check_login
def show_index():
    return redirect('/static/index.html')


@app.route('/captcha')
def get_captcha_image():
    cap = captcha.Captcha.instance()  # type: captcha.Captcha
    captcha_code = random_captcha_code()
    session['captcha_code'] = captcha_code.lower()
    cap_image_data = cap.generate(captcha_code)
    resp = make_response(cap_image_data)
    resp.headers['content-type'] = 'image/png'
    return resp


@app.route('/login', methods=['POST', ])
def login():
    params = request.json
    captcha_from_user = params.get('captcha').lower()
    captcha_from_sess = session.get('captcha_code')
    if captcha_from_sess != captcha_from_user:
        return {'code': 10001, 'message': '验证码错误'}
    username = params.get('username')
    password = params.get('password')
    password = hashlib.md5(password.encode()).hexdigest()
    if username == '' or password == '':
        return {'code': 10001, 'message': '用户名或密码不能为空'}
    conn = get_mysql_connection()
    try:
        with conn.cursor(pymysql.cursors.DictCursor) as cursor:
            cursor.execute('select user_id, nickname, avatar from tb_user where username=%s and userpass=%s',
                           (username, password)
            )
            info_dict = cursor.fetchone()
    except pymysql.MySQLError as err:
        print(err)
    finally:
        conn.close()
    if info_dict is None:
        return {'code': 10002, 'message': '用户名或密码错误'}
    session['user_id'] = info_dict['user_id']
    session.permanent = True
    nickname, avatar = info_dict['nickname'], info_dict['avatar']
    return {'code': 10000, 'message': '登录成功', 'nickname': nickname, 'avatar': avatar}


@app.route('/export')
@check_login
def export_excel():
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.append(('交易日', '开盘价', '收盘价', '最低价', '最高价', '交易量'))
    conn = get_mysql_connection(database='stock')
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                'select trade_date, open_price, close_price, '
                'low_price, high_price, trade_volume '
                'from tb_baba_stock order by stock_id'
            )
            for row in cursor.fetchall():
                sheet.append(row)
    finally:
        conn.close()
    buffer = io.BytesIO()
    wb.save(buffer)
    resp = make_response(buffer.getvalue())
    resp.headers['content-type'] = 'application/vnd.ms-excel'
    resp.headers['content-disposition'] = f'attachment; filename="stocks.xlsx"'
    return resp


@app.errorhandler(404)
def show_error_page(error):
    return redirect('/static/lyear_pages_error.html')



@app.route('/logout')
@check_login
def logout():
    session.clear()
    return {'code': 10003, 'message': '退出登录'}


if __name__ == '__main__':
    app.run(port=8000, debug=True)
