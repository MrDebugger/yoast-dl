from requests import Session,get
from tqdm import tqdm
from bs4 import BeautifulSoup as bs
from urllib.parse import urlparse
import json,os,slug
import argparse
from sys import argv
def login(email,password):
    headers = {
        'authority': 'my.yoast.com',
        'sec-fetch-dest': 'empty',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.149 Safari/537.36',
        'content-type': 'application/json',
        'accept': '*/*',
        'origin': 'https://my.yoast.com',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-mode': 'cors',
        'referer': 'https://my.yoast.com/login',
        'accept-language': 'en-US,en;q=0.9',
    }
    params = (
        ('access_token', ''),
    )
    data = {"email":email,"password":password,"rememberMe":False,"otp":""}
    ses = Session()
    ses.headers.update(headers)
    ses.get('https://my.yoast.com/login')
    response = ses.post('https://my.yoast.com/api/Customers/login-user/', params=params, json=data)
    return ses

def main():
    parser = argparse.ArgumentParser(description='', usage=f'\npython {argv[0]} [options]')
    parser._optionals.title = "Basic Help"
    basicFuncs  = parser.add_argument_group('Actions')
    basicFuncs.add_argument('-u','--email', action="store", dest="email", default=False, help='Email for Yoast')    
    basicFuncs.add_argument('-p','--password', action="store", dest="password", default=False, help='Password for Yoast') 
    basicFuncs.add_argument('-c','--course-url', action="store", dest="course_url", default=False, help='Course URL')   
    args = parser.parse_args()
    if not(args.email and args.password and args.course_url):
        parser.print_help()
        return
    COURSE_URL = args.course_url
    MAIN_SITE = f"{urlparse(COURSE_URL).scheme}://{urlparse(COURSE_URL).netloc}"
    ses = login(args.email,args.password)
    r = ses.get(COURSE_URL)
    soup = bs(r.text,'lxml')
    try:
        courseTitle = soup.find(class_='gtm__course-title').get_text(strip=True)
    except:
        print("[-] Unable to Download the Course")
        return 
    print("[+] Course:",courseTitle)
    if not os.path.exists(courseTitle):
        os.mkdir(courseTitle)
    if soup.findAll(class_='wistia_embed'):
        print("[>] Video Found in Overview Page")
        for video in soup.findAll(class_='wistia_embed'):
            print("[+] Getting JSON Data")
            videoUrl,videoName,videoExt = getVideo(video)
            print("[>] Downloading Video")
            download_file(videoUrl,os.path.join(courseTitle,videoName+'.'+videoExt))
    print()
    chapters = [(chapter,chapter.find('a').get_text(strip=True)) for chapter in soup.findAll(class_='list_lessons')]
    chapterId = 1
    for chapter in chapters:
        chapterData = chapter[0]
        chapterName = chapter[1]
        print("[+] Chapter:",chapterName)
        chapterName = slug.slug(chapterName)
        path = os.path.join(courseTitle,chapterName)
        if not os.path.exists(path):
            os.mkdir(path)
        lessons = [(topic.find('a').get('href'),topic.find('a').get_text(strip=True)) for topic in chapterData.findAll(class_='topic_item')]
        for lesson in lessons:
            lessonUrl = lesson[0]
            lessonName = lesson[1]
            print("[+] Lesson:",lessonName)
            r = ses.get(lessonUrl)
            soup = bs(r.text,'lxml')
            topics = soup.findAll(class_='h3')[:-1]
            for topic in topics:
                topicName = topic.get_text(strip=True)
                print("[+] Topic:",topicName)
                videoTag = topic.next_sibling.next_sibling.next_sibling.next_sibling
                if not videoTag.find(class_='wistia_embed'):
                    videoTag = videoTag.previous_sibling.previous_sibling
                    print("[+] PDF File Found")
                    videoUrl= videoTag.find('a').get('href')
                    videoName = '.'.join(videoUrl.split('/')[-1].split('.')[:-1])
                    videoExt = videoUrl.split('.')[-1]
                else:
                    print("[+] Video Found")
                    videoUrl,videoName,videoExt = getVideo(videoTag.find(class_='wistia_embed'))
                videoName = slug.slug(videoName)
                print("[>] Downloading")
                download_file(videoUrl,os.path.join(path,videoName+'.'+videoExt))
                print("[+] Downloaded")
                print()
    print("Completed")
def getVideo(soup):
    videoTag = soup.get('class')[1].replace('wistia_async_','')
    jsonUrl = f"https://fast.wistia.com/embed/medias/{videoTag}.json"
    r = get(jsonUrl)
    jsonData = r.json()
    video = jsonData['media']['assets'][0]
    videoExt = video.get('ext','mp4')
    videoUrl = video['url']
    videoName = jsonData['media']['name']
    return videoUrl,videoName,videoExt

def download_file(url,name):
    local_filename = name
    headers = {}
    if os.path.exists(local_filename):
        headers = {'Range': 'bytes=%d-' % (os.path.getsize(local_filename))}
        print("[>] Resuming Video")
    with get(url, stream=True,headers=headers) as r:
        if not r and headers:
            print("[+] Video Already Downloaded")
            return
        total_size = int(r.headers.get('content-length', 0))
        t=tqdm(total=total_size, unit='iB', unit_scale=True)
        r.raise_for_status()
        with open(local_filename, 'ab') as f:
            for chunk in r.iter_content(chunk_size=8192): 
                t.update(len(chunk))
                if chunk: 
                    f.write(chunk)
        t.close()
        if total_size != 0 and t.n != total_size:
            print("ERROR, something went wrong")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n[-] Program Cancelled")