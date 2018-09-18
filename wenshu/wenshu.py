import requests
import execjs
from urllib import parse
from pymongo import MongoClient
import json
import re
import os

conn = MongoClient('192.168.0.112', 27017)
db = conn.wsdb
ws_set = db.ws_set


session = requests.Session()
with open('vl5x.js') as fp:
    js = fp.read()
    ctx = execjs.compile(js)

with open('aesb64.js') as fp:
    js = fp.read()
    ctx2 = execjs.compile(js)


res =requests.session()
def get_guid():

    jsguid = '''
      function getGuid() {
            var guid = createGuid() + createGuid() + "-" + createGuid() + "-" + createGuid() + createGuid() + "-" + createGuid() + createGuid() + createGuid(); //CreateGuid();
              return guid;
        }
        var createGuid = function () {
            return (((1 + Math.random()) * 0x10000) | 0).toString(16).substring(1);
        }
    '''
    js1 = execjs.compile(jsguid)
    guid = (js1.call("getGuid"))
    return guid



def get_number(guid):
    #获取number
    codeUrl = "http://wenshu.court.gov.cn/ValiCode/GetCode"
    data = {
        'guid':guid
    }
    headers = {
        'Host':'wenshu.court.gov.cn',
        'Origin':'http://wenshu.court.gov.cn',
        'Referer':'http://wenshu.court.gov.cn/',
        'User-Agent':'Mozilla/5.0(Macintosh;IntelMacOSX10_7_0)AppleWebKit/535.11(KHTML,likeGecko)Chrome/17.0.963.56Safari/535.11'
    }
    req1 = res.post(codeUrl,data=data,headers=headers)
    number = req1.text
    return number

def get_vjkl5(guid,number,Param):
    #获取vik15
    url1 = "http://wenshu.court.gov.cn/list/list/?sorttype=1&number="+number+"&guid="+guid+"&conditions=searchWord+QWJS+++"+parse.quote(Param)
    headers2 = {
        "Accept":"text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
        "Accept-Encoding":"gzip, deflate",
        "Accept-Language":"zh-CN,zh;q=0.8",
        "Host":"wenshu.court.gov.cn",
        "Proxy-Connection":"keep-alive",
        "Upgrade-Insecure-Requests":"1",
        "User-Agent":"Mozilla/5.0(Macintosh;IntelMacOSX10_7_0)AppleWebKit/535.11(KHTML,likeGecko)Chrome/17.0.963.56Safari/535.11"
    }
    req1 = res.get(url=url1,headers=headers2,timeout=5)
    try:
        vjkl5 = req1.cookies["vjkl5"]
        return vjkl5
    except:
        return get_vjkl5(guid,number,Param)

def get_vl5x(vjkl5):
    #通过vjkl5获取参数vl5x

    vl5x = (ctx.call('GetVl5x',vjkl5))
    return vl5x



def decrypt_id(RunEval, id):
    #docid解密

    js = ctx2.call("GetJs", RunEval)
    js_objs = js.split(";;")
    js1 = js_objs[0] + ';'
    js2 = re.findall(r"_\[_\]\[_\]\((.*?)\)\(\);", js_objs[1])[0]
    key = ctx2.call("EvalKey", js1, js2)
    key = re.findall(r"\"([0-9a-z]{32})\"", key)[0]
    docid = ctx2.call("DecryptDocID", key, id)
    return docid



def get_data(Param,Page,Order,Direction):

    Index = 1       #第几页

    guid = get_guid()
    number = get_number(guid)
    vjkl5 = get_vjkl5(guid,number,Param)
    vl5x = get_vl5x(vjkl5)

    while(True):

        print('第{0}页 '.format(Index))

        #获取数据
        url = "http://wenshu.court.gov.cn/List/ListContent"
        headers = {
            "Accept":"*/*",
            "Accept-Encoding":"gzip, deflate",
            "Accept-Language":"zh-CN,zh;q=0.8",
            "Content-Type":"application/x-www-form-urlencoded; charset=UTF-8",
            "Host":"wenshu.court.gov.cn",
            "Origin":"http://wenshu.court.gov.cn",
            "Proxy-Connection":"keep-alive",
            "Referer":"http://wenshu.court.gov.cn/list/list/?sorttype=1&number={0}&guid={1}&conditions=searchWord+QWJS+++{2}".format(number,guid,parse.quote(Param)),
            "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.101 Safari/537.36",
            "X-Requested-With":"XMLHttpRequest"
        }
        data = {
            "Param":Param,
            "Index":Index,
            "Page":Page,
            "Order":Order,
            "Direction":Direction,
            "vl5x":vl5x,
            "number":number,
            "guid":guid
        }

        req = session.post(url,headers=headers,data=data)
        req.encoding = 'utf-8'
        return_data = req.text.replace('\\','').replace('"[','[').replace(']"',']')\
                    .replace('＆ｌｄｑｕｏ;', '“').replace('＆ｒｄｑｕｏ;', '”')

        if return_data == '"remind"' or return_data == '"remind key"':
            print('爬取失败')
            os.system("pause")

        else:
            json_data = json.loads(return_data)
            if not len(json_data):
                print('采集完成')
                break
            else:
                RunEval = json_data[0]['RunEval']
                for i in range(1,len(json_data)):
                    name = json_data[i]['案件名称'] if '案件名称' in json_data[i] else ''
                    court = json_data[i]['法院名称'] if '法院名称' in json_data[i] else ''
                    number = json_data[i]['案号'] if '案号' in json_data[i] else ''
                    type = json_data[i]['案件类型'] if '案件类型' in json_data[i] else ''
                    id = json_data[i]['文书ID'] if '文书ID' in json_data[i] else ''
                    id = decrypt_id(RunEval, id)
                    date = json_data[i]['裁判日期'] if '裁判日期' in json_data[i] else ''
                    data_dict = dict(
                                    id=id,
                                    name=name,
                                    type=type,
                                    date=date,
                                    number=number,
                                    court=court
                                )
                    save_data(data_dict)
                    print(data_dict)

            Index += 1

            guid = get_guid()
            number = get_number(guid)

        if Index == 10:
            break

def save_data(data_dict):
    try:
        ws_set.insert(data_dict)
    except Exception as e:
        print(e)

def getCourtInfo(DocID):
    """
    根据文书DocID获取内容
    """
    url = 'http://wenshu.court.gov.cn/CreateContentJS/CreateContentJS.aspx?DocID={0}'.format(DocID)
    headers = {
        'Host':'wenshu.court.gov.cn',
        'Origin':'http://wenshu.court.gov.cn',
        'User-Agent':'Mozilla/5.0(Macintosh;IntelMacOSX10_7_0)AppleWebKit/535.11(KHTML,likeGecko)Chrome/17.0.963.56Safari/535.11',
    }
    req = requests.get(url,headers=headers)
    req.encoding = 'uttf-8'
    return_data = req.text.replace('\\','')
    read_count = re.findall(r'"浏览\：(\d*)次"',return_data)[0]
    court_title = re.findall(r'\"Title\"\:\"(.*?)\"',return_data)[0]
    court_date = re.findall(r'\"PubDate\"\:\"(.*?)\"',return_data)[0]
    court_content = re.findall(r'\"Html\"\:\"(.*?)\"',return_data)[0]
    return [court_title,court_date,read_count,court_content]

def download(DocID):
    """
    根据文书DocID下载doc文档
    """
    courtInfo = getCourtInfo(DocID)
    url = 'http://wenshu.court.gov.cn/Content/GetHtml2Word'
    headers = {
        'Host':'wenshu.court.gov.cn',
        'Origin':'http://wenshu.court.gov.cn',
        'User-Agent':'Mozilla/5.0(Macintosh;IntelMacOSX10_7_0)AppleWebKit/535.11(KHTML,likeGecko)Chrome/17.0.963.56Safari/535.11',
    }
    fp = open('content.html','r',encoding='utf-8')
    htmlStr = fp.read()
    fp.close()
    htmlStr = htmlStr.replace('court_title',courtInfo[0]).replace('court_date',courtInfo[1]).\
        replace('read_count',courtInfo[2]).replace('court_content',courtInfo[3])
    htmlName = courtInfo[0]
    data = {
        'htmlStr':parse.quote(htmlStr),
        'htmlName':parse.quote(htmlName),
        'DocID':DocID
    }
    req = session.post(url,headers=headers,data=data)
    filename = './download/{}.doc'.format(htmlName)
    fp = open('{}.doc'.format(htmlName),'wb')
    fp.write(req.content)
    fp.close()
    print('"{}"文件下载完成...'.format(filename))

if __name__ == '__main__':

    #### 检索条件 ####

    Param = "全文检索:经济纠纷"
    Page = 20       #每页几条
    Order = "法院层级"  #排序标准
    Direction = "asc"
    get_data(Param,Page,Order,Direction)

