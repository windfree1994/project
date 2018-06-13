import random

from flask import current_app, jsonify
from flask import json
from flask import make_response
from flask import request

from info import constants, db
from info import redis_store
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.captcha.captcha import captcha
from info.utils.response_code import RET
from . import passport_blu
# 注册用户
# 请求路径: /passport/register
# 请求方式: POST
# 请求参数: mobile, sms_code,password
# 返回值: errno, errmsg
@passport_blu.route('/register',methods=['POST'])
def register():
    # 获取参数
    dict_data = request.json
    mobile = dict_data.get('mobile')
    sms_code = dict_data.get('sms_code')
    password = dict_data.get('password')
    # 校验参数
    if not all([mobile,sms_code,password]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不完整')

    # 通过手机号获取redis中的短信验证码
    try:
        redis_sms_code=redis_store.get('sms_code:%s'%mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR,errmsg='短信验证码获取异常')
    # 判断短信验证码是否过期
    if sms_code !=redis_sms_code:
        return jsonify(errno=RET.NODATA,errmsg='短信验证码已过期')
    # 判断验证码正确性
    if sms_code !=redis_sms_code:
        return jsonify(errno =RET.DATAERR,errmsg='短信验证码输入错误')
    # 创建用户对象设置对象属性
    user =User()
    user.nick_name=mobile
    user.mobile = mobile
    #TODO 未加密

    user.password_hash=password
    # 保存到数据库中
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR,errmsg='用户保存异常')
    # 返回注册到前段页面
    return jsonify(errno=RET.OK,errmsg='注册成功')


# 生成短信验证码
# 请求路径: /passport/sms_code
# 请求方式: POST
# 请求参数: mobile, image_code,image_code_id
# 返回值: errno, errmsg
@passport_blu.route('/sms_code',methods=['POST'])
def set_sms_code():
    """
    # 1获取参数
    # 2校验参数
    # 3根据图片验证码编号获取redis中的图片验证码
    # 4判断是否过期
    # 5判断图片验证码是否相等
    # 6生成短信验证码
    # 7发送短信，调用ccp.send_template_sms方法
    # 8保存短信验证码到redis中
    #9.返回前段浏览器
    :return:
    """
    """
    获取Post 请求提数据，解析成字典格式的三种方法
    1.json_data=request.data  dict_data = json.loads(json_data)
    2.dict_data=request.get_json()
    3.dict_data=request.json
    """
    # 1获取参数
    json_data=request.data
    dict_data=json.loads(json_data)
    mobile=dict_data.get('mobile')
    image_code = dict_data.get('image_code')
    image_code_id = dict_data.get('image_code_id')

    # 2校验参数
    if not all([mobile,image_code,image_code_id]):
        return jsonify(errno=RET.PARAMERR,errmsg='参数不能为空')
    # 3根据图片验证码编号获取redis中的图片验证码
    try:
        redis_image_code=redis_store.get('image_code:%s'%image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 4判断是否过期
    if not redis_image_code:
        return jsonify(errno=RET.NODATA,errmsg='图片验证码已过期')
    # 5判断图片验证码是否相等
    if image_code.lower()!=redis_image_code.lower():
        return jsonify(errno=RET.DATAERR,errmsg='图片验证码填写错误')
    # 可以删除图片验证码
    try:
        redis_store.delete('image_code:%s'%image_code_id)
    except Exception as e:
        current_app.logger.error(e)
    # 6生成短信验证码
    sms_code="%06d"%random.randint(0,999999)
    # 7发送短信，调用ccp.send_template_sms方法
    ccp = CCP()
    result=ccp.send_template_sms(mobile,[sms_code,5],1)

    if result ==-1:
        return jsonify(errno=RET.THIRDERR,errmsg='短信发送失败')
    # 8保存短信验证码到redis中
    try:
        redis_store.set('sms_code:%s'%mobile,sms_code,constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
    # 9.返回前段浏览器
    return jsonify(errno=RET.OK,errmsg='发送成功')
# 生成图片验证码
# 请求路径: /passport/image_code
# 请求方式: GET
# 请求参数: cur_id, pre_id
# 返回值: 图片验证码
@passport_blu.route('/image_code')
def get_image_code():

    # 1.获取参数，随机字符串。args获取请求地址？后的参数
    cur_id=request.args.get('cur_id')
    pre_id=request.args.get('pre_id')
    # 2.生成图片验证码
    name,text,image_data=captcha.generate_captcha()
    # 3.保存到redis
    try:
        redis_store.set('image_code:%s'%cur_id,text,constants.IMAGE_CODE_REDIS_EXPIRES)
        # 如果有上一个图片验证码 删除
        if pre_id:
            redis_store.delete('image_code%s'%pre_id)
    except Exception as e:
        current_app.logger.error(e)
    # 4.返回到前段浏览器
    response=make_response(image_data)
    response.headers['Content-Type']='image/jpg'
    return response

