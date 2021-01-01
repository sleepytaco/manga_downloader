import shutil
import sys
from PIL.Image import Image
import requests
import send2trash
from bs4 import BeautifulSoup
from selenium import webdriver
from pathlib import Path
import os
import re
import time

"""
Supported sites:
https://mangakakalot.com/
https://manganelo.com/manga/
https://m.manganelo.com
"""

PROGRAM_LOCATION = Path.cwd()
WEBDRIVER_LOCATION = Path.cwd() / 'driver'
SETTINGS_LOCATION = PROGRAM_LOCATION / "settings.txt"


def get_soup(site, headers=''):
    if headers == '':  # if headers not specified, uses default
        headers = {'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0'}
    r = requests.get(site, headers=headers)
    soup = BeautifulSoup(r.text, 'lxml')

    return soup


def get_setting(setting):  # gets setting from settings.txt
    with open(SETTINGS_LOCATION, "r", encoding="utf-8") as settings_file:
        while True:
            line = settings_file.readline()
            if setting in line:
                return line.split(":")[-1].strip()


def download_image(image_url, image_name='', overwrite_name=False):
    if image_name == '':  # if image name not a string, use image name from link
        image_name = os.path.basename(image_url)
    else:  # else uses specified image name and adds proper extension at the end
        if '.jpg' in os.path.basename(image_url) or '.jpeg' in os.path.basename(
                image_url) or '.png' in os.path.basename(image_url) or '.gif' in os.path.basename(
            image_url) or '.tiff' in os.path.basename(image_url):
            image_name = image_name.strip() + '.' + os.path.basename(image_url).split('.')[-1]
            images_in_current_folder = os.listdir(os.getcwd())  # get all available
            if image_name in images_in_current_folder:
                if not overwrite_name:
                    print(
                        f"Did not download image because an image named '{image_name}' already exists in the current folder.")
                    return -1
        else:  # if proper extension for the image is not found
            print("Unable to download image because image extension could not be found. Image extension found:",
                  os.path.basename(image_url))
            return -2

    r = requests.get(image_url.replace('\r', ''), stream=True, headers={
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.116 Safari/537.36 OPR/69.0.3686.49'})

    # Check if the image was retrieved successfully
    if r.status_code == 200:
        # Set decode_content value to True, otherwise the downloaded image file's size will be zero.
        r.raw.decode_content = True
        # Open a local file with wb ( write binary ) permission.
        with open(image_name, 'wb') as f:
            shutil.copyfileobj(r.raw, f)

    return r.status_code


def move_to_download_folder(DOWNLOAD_FOLDER):
    print(f"\nChecking if the download folder exists...")
    if os.path.isdir(DOWNLOAD_FOLDER):
        print("--> Found the download folder.")
    else:
        if not os.path.isdir("Manga Downloads"):
            os.mkdir("Manga Downloads")
            print(f"Did not find the specified download folder.\n"
                  f"Created a new folder named Manga Downloads/ in the program location and moved to it.")
        else:
            print(f"Moved to {Path.cwd() / 'Manga Downloads'}")
        DOWNLOAD_FOLDER = Path.cwd() / 'Manga Downloads'
    return DOWNLOAD_FOLDER


def download_poster(manga_poster_link):
    if 'poster.jpg' in os.listdir(os.getcwd()) or 'poster.jpeg' in os.listdir(
            os.getcwd()) or 'poster.png' in os.listdir(os.getcwd()):
        print(f"\n--> Manga poster already downloaded.")
    else:
        # print(f"\nDownloading poster '{os.path.basename(manga_poster_link)}'...")
        print(f"\nDownloading manga poster...")
        status = download_image(manga_poster_link, image_name='poster', overwrite_name=True)
        if status == 200:
            print("Downloaded poster.")
        else:
            print(f"!!! Unable to download '{os.path.basename(manga_poster_link)}'. Staus Code: {status}\n"
                  f"Poster Image Link: {manga_poster_link}")


class Mangakakalot:

    def __init__(self, manga_page):
        self.manga_page = manga_page

    def get_ready(self):  # perform sanity checks before starting the downloads

        DOWNLOAD_FOLDER = move_to_download_folder(Path(get_setting('DOWNLOADS DIRECTORY')))

        os.chdir(DOWNLOAD_FOLDER)

        #### SCRAPE MANGA INFO ####
        soup = get_soup(self.manga_page)
        print(f"\nGetting manga info from {self.manga_page} ...")
        try:
            manga_title = soup.select('ul > li > h1', class_="manga-info-text")[0].text.upper()
            manga_poster_link = \
            soup.select(f'''img[alt="{soup.select('ul > li > h1', class_="manga-info-text")[0].text}"]''')[
                0].get('src')
            manga_status = soup.select('ul > li:nth-of-type(3)', class_="manga-info-text")[-1].text.split(":")[
            -1].strip().upper()
            latest_chapter = soup.select('div > div > span > a', class_='chapter-list')[0].text
        except IndexError:
            print(
                f"Looks like page does not exist :(\nMake sure you copy the link of the main manga page (eg. https://manganelo.com/manga/read_boku_no_hero_academia_manga)\n"
                f"Check Page: {self.manga_page}")
            sys.exit()

        
        manga_title = manga_title.replace(":", ";").replace("?",
                                                            "!").replace(
            '"', "'").replace("\\", "").replace("/", "").replace("|", "-or-").replace("*", "!").replace("<",
                                                                                                        "-less-than-").replace(
            ">", "-greater-than-").replace('.', '')

        print(f"\n"
              f"Manga Title: {manga_title}\n"
              f"Manga Status: {manga_status}\n"
              f"Latest Chapters: {latest_chapter}")

        #### GET ALL CHAPTER LINKS ####
        CHAPTER_LINK_ELTS = soup.select('div > div > span > a', class_='chapter-list')
        print(f"\nFound {len(CHAPTER_LINK_ELTS)} chapter links.\n")
        CHAPTER_LINK_ELTS.reverse()

        ### DISPLAY ALL CHAPTER NAMES ###
        d = {}
        for c in range(len(CHAPTER_LINK_ELTS)):
            d[c] = CHAPTER_LINK_ELTS[c].text
        print(d)

        if get_setting('DOWNLOAD ALL CHAPTERS').strip().upper() != 'YES':
            chapter_range = str(input(f"\nEnter range (eg. 0-{len(CHAPTER_LINK_ELTS) - 1}): "))

            if chapter_range == '':
                print("\nVery well, downloading all", len(CHAPTER_LINK_ELTS), "chapters")
            else:
                rangeRegex = re.compile(r'\d+\s*-\s*\d+')
                r = rangeRegex.search(chapter_range)

                while r is None:
                    print("Enter a valid range in the form [number]-[number]")
                    chapter_range = str(input(f"\nEnter range (eg. 0-{len(CHAPTER_LINK_ELTS) - 1}): "))
                    r = rangeRegex.search(chapter_range)

                    if r is None:
                        continue

                    start, end = r.group().split("-")
                    if 0 <= int(end) <= len(CHAPTER_LINK_ELTS) - 1 and 0 <= int(start) <= int(end) - 1:
                        if not int(start) <= int(end):
                            r = None
                    else:
                        r = None

                new_range = r.group().split("-")
                CHAPTER_LINK_ELTS = CHAPTER_LINK_ELTS[int(new_range[0]):int(new_range[1]) + 1]

                print(f"\nWill download {len(CHAPTER_LINK_ELTS)} chapters.")
                time.sleep(1)

        #### CREATE A NEW FOLDER FOR THE MANGA ####
        print("\nChecking if Manga folder exists...")
        if os.path.isdir(Path(DOWNLOAD_FOLDER) / f'{manga_title}'):
            print("--> Found the download folder. Will download new chapters into it.")
        else:
            os.mkdir(DOWNLOAD_FOLDER / f'{manga_title}')
            print(f"Created a new folder {DOWNLOAD_FOLDER / f'{manga_title}'} and moved to it.")

        os.chdir(DOWNLOAD_FOLDER / f'{manga_title}')  # move to respective manga folder

        download_poster(manga_poster_link)

        ### MAKE HTML FOR MAIN PAGE ####
        chapter_website = open(manga_title + '.html', 'w')
        chapter_website.write(f'''<meta http-equiv="Refresh" content="0; url='{self.manga_page}'" />''')
        chapter_website.close()

        #### STORE MANGA INFO IN TXT FILE ####
        print("\nStored Manga details into text file.")
        empty_file = open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'w', encoding="utf-8")
        empty_file.close()
        with open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'a',
                  encoding="utf-8") as manga_info_file:
            manga_info_file.write(f"Manga: {manga_title}\n")
            manga_info_file.write(f"Status: {manga_status}\n")
            manga_info_file.write(f"Latest Chapter: {latest_chapter}\n")
            manga_info_file.write(f"Total Chapter Count: {len(CHAPTER_LINK_ELTS)}" + "\n")
            manga_info_file.write("\n" + f"Manga Site: {self.manga_page}")

        return manga_title, manga_status, latest_chapter, DOWNLOAD_FOLDER, CHAPTER_LINK_ELTS

    def download(self, download_details):

        manga_title = download_details[0]
        manga_status = download_details[1]
        latest_chapter = download_details[2]
        DOWNLOAD_FOLDER = download_details[3]
        CHAPTER_LINK_ELTS = download_details[4]

        if get_setting('CONFIRM BEFORE STARTING DOWNLOADS').upper() == 'YES':
            input("\nPress enter to start downloading...")

        print("\n----- STARTING DOWNLOADS -----")
        print("\nOpening Firefox...")

        try:
            browser = webdriver.Firefox(WEBDRIVER_LOCATION)
        except OSError:
            print("\nUh-oh looks like Selenium has trouble running on your OS. This script has been tested and works on Ubuntu 20, Windows 8.1 and Windows 10.")
            input('\nPress Enter to quit.')
            sys.exit()
        except:
            print("\nScript is having trouble opening up Firefox on your computer. Try the following:\n1. Make sure you have the latest version of Firefox installed.\n2. Check if the driver folder is in the same location as the .exe file or main.py and run the program again.")
            input('\nPress Enter to quit.')
            sys.exit()


        browser.implicitly_wait(10)

        count = 1
        newly_downloaded = []
        not_fully_downloaded = []
        already_downloaded = []

        for elt in CHAPTER_LINK_ELTS:
            os.chdir(DOWNLOAD_FOLDER / f'{manga_title}')  # move to respective manga folder
            print(f"\n##### Link {count} of {len(CHAPTER_LINK_ELTS)} #####")

            print("Opening", elt['href'], "...")
            browser.get(elt['href'])

            img_elts = browser.find_elements_by_xpath("//div[@id='vungdoc'][@class='vung-doc']/img")

            print(f"Found {len(img_elts)} pages.")

            chapter_name = elt.text
            chapter_name = chapter_name.replace(":", " -").replace("?",
                                                                   "!").replace(
                '"', "'").replace("\\", "").replace("/", "").replace("|", "-or-").replace("*", "!").replace("<",
                                                                                                            "-less-than-").replace(
                ">", "-greater-than-").strip()

            # create respective chapter folder and move to it
            if chapter_name in os.listdir(os.getcwd()):
                print(f"--> Chapter folder '{chapter_name}' exists.")
            else:
                try:
                    os.mkdir(chapter_name)
                    print(f"Created a folder named '{chapter_name}' to download pages into.")
                except FileExistsError:
                    print(f"--> Chapter folder '{chapter_name}' exists.")
            os.chdir(chapter_name)

            # save webpage link in html to the chapter in the folder
            chapter_website = open(chapter_name + '.html', 'w')
            chapter_website.write(f'''<meta http-equiv="Refresh" content="0; url='{elt['href']}'" />''')
            chapter_website.close()

            if len(os.listdir(os.getcwd())) == len(img_elts) + 1:
                print("ALL IMAGE LINKS DOWNLOADED.")
                already_downloaded.append(chapter_name)
                count += 1
                continue

            print(f"DOWNLOADING {manga_title.upper()} {chapter_name.upper()}")

            # download images into that chapter folder
            for img in img_elts:
                if os.path.basename(img.get_attribute('src')) in os.listdir(os.getcwd()):
                    print(f"'{os.path.basename(img.get_attribute('src'))}' already downloaded.")
                    continue
                try:
                    if os.path.basename(img.get_attribute('src')).endswith(('.jpg', '.jpeg')):
                        print(f"Downloading '{os.path.basename(img.get_attribute('src')).replace('.jpg', '.png')}' ...")
                        img.screenshot(os.path.basename(img.get_attribute('src')).replace('.jpg', '.png'))
                    else:
                        print(f"Downloading '{os.path.basename(img.get_attribute('src'))}' ...")
                        img.screenshot(os.path.basename(img.get_attribute('src')))
                except:
                    print("!!!Unable to screenshot this image element. Will attempt to download it via requests.")
                    status = download_image(img.get_attribute('src'))
                    if status == 200:
                        # if image downloaded
                        im = Image.open(f"{os.path.basename(img.get_attribute('src'))}").convert("RGB")
                        im.save(os.path.basename(img.get_attribute('src')).replace('.jpg', '.png'), 'png')
                        send2trash.send2trash(os.path.basename(img.get_attribute('src')))
                    else:
                        print(f"!!!Unable to download image. Status Code:{status}. Link: {img.get_attribute('src')}")
                        print("Will screenshot the element again if possible.")
                        if os.path.basename(img.get_attribute('src')).endswith(('.jpg', '.jpeg')):
                            print(
                                f"Downloading '{os.path.basename(img.get_attribute('src')).replace('.jpg', '.png')}' ...")
                            img.screenshot(os.path.basename(img.get_attribute('src')).replace('.jpg', '.png'))
                        else:
                            print(f"Downloading '{os.path.basename(img.get_attribute('src'))}' ...")
                            img.screenshot(os.path.basename(img.get_attribute('src')))

            os.chdir(DOWNLOAD_FOLDER / f'{manga_title}')  # move back to respective manga folder
            print("DONE.")
            newly_downloaded.append(chapter_name)
            count += 1
        browser.close()
        print("\n----- DONE DOWNLOADING -----")

        print(f"\n{len(CHAPTER_LINK_ELTS)} total links found\n"
              f"{len(newly_downloaded)} newly downloaded chapters\n"
              f"{len(not_fully_downloaded)} chapters not fully downloaded\n"
              f"{len(already_downloaded)} chapters already downloaded")

        if len(not_fully_downloaded) != 0:
            print(f"\nWas not able to fully download the following {len(not_fully_downloaded)} chapters:")
            print('\n'.join(not_fully_downloaded))

            ##### update manga info in the text file
            empty_file = open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'w', encoding="utf-8")
            empty_file.close()
            with open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'a',
                      encoding="utf-8") as manga_info_file:
                manga_info_file.write(f"Manga: {manga_title}\n")
                manga_info_file.write(f"Status: {manga_status}\n")
                manga_info_file.write(f"Latest Chapter: {latest_chapter}\n")
                manga_info_file.write(f"Total Chapter Count: {len(CHAPTER_LINK_ELTS)}" + "\n")
                manga_info_file.write(
                    f"\nWas not able to fully download the following {len(not_fully_downloaded)} chapters:")
                manga_info_file.write("\n" + '\n'.join(not_fully_downloaded))
                manga_info_file.write("\n\n" + f"Manga Site: {self.manga_page}")
            os.rename(f"{manga_title.lower()} info (STATUS - {manga_status}).txt",
                      f"{manga_title.lower()} info (STATUS - ATTN REQUIRED).txt")
            print(f"\nUpdated manga details in '{manga_title.lower() + f' info (STATUS - ATTN REQUIRED).txt'}'.")
        
        os.system(f'start %windir%\\explorer.exe "{DOWNLOAD_FOLDER / manga_title}"')


class Manganelo:

    def __init__(self, manga_page):
        self.manga_page = manga_page

    def get_ready(self):  # perform sanity checks before starting the downloads

        DOWNLOAD_FOLDER = move_to_download_folder(Path(get_setting('DOWNLOADS DIRECTORY')))

        os.chdir(DOWNLOAD_FOLDER)

        #### SCRAPE MANGA INFO ####
        soup = get_soup(self.manga_page)
        print(f"\nGetting manga info from {self.manga_page} ...")
        try:
            manga_title = soup.select('div > h1', class_='story-info-right')[0].text.upper()
            manga_poster_link = soup.select('span > img', class_='img-loading')[0]['src']
            manga_status = \
                soup.select('table > tbody > tr:nth-of-type(3) > td:nth-of-type(2)', class_='variations-tableInfo')[
                    0].text.strip().upper()
            latest_chapter = soup.select('ul > li > a', class_='row-content-chapter')[0].text.replace(":", " -")
        except IndexError:
            print(
                f"\nLooks like I crashed :(\nMake sure you copy the link of the main manga page (eg. https://manganelo.com/manga/read_boku_no_hero_academia_manga)\n"
                f"Check Page: {self.manga_page}\n")
            input("Press Enter to exit.")
            sys.exit()

        manga_title = manga_title.replace(":", ";").replace("?",
                                                            "!").replace(
            '"', "'").replace("\\", "").replace("/", "").replace("|", "-or-").replace("*", "!").replace("<",
                                                                                                        "-less-than-").replace(
            ">", "-greater-than-").replace('.', '')

        print(f"\n"
              f"Manga Title: {manga_title}\n"
              f"Manga Status: {manga_status}\n"
              f"Latest Chapters: {latest_chapter}")

        #### GET ALL CHAPTER LINKS ####
        CHAPTER_LINK_ELTS = soup.find_all('a', class_='chapter-name text-nowrap')
        print(f"\nFound {len(CHAPTER_LINK_ELTS)} chapter links.")
        CHAPTER_LINK_ELTS.reverse()

        d = {}
        for c in range(len(CHAPTER_LINK_ELTS)):
            d[c] = CHAPTER_LINK_ELTS[c].text
        print(d)

        if get_setting('DOWNLOAD ALL CHAPTERS').strip().upper() != 'YES':
            chapter_range = str(input(f"\nEnter range (eg. 0-{len(CHAPTER_LINK_ELTS) - 1}): "))

            if chapter_range == '':
                print("\nVery well, downloading all", len(CHAPTER_LINK_ELTS), "chapters")
            else:
                rangeRegex = re.compile(r'\d+\s*-\s*\d+')
                r = rangeRegex.search(chapter_range)

                while r is None:
                    print("Enter a valid range in the form [number]-[number]")
                    chapter_range = str(input(f"\nEnter range (eg. 0-{len(CHAPTER_LINK_ELTS) - 1}): "))
                    r = rangeRegex.search(chapter_range)

                    if r is None:
                        continue

                    start, end = r.group().split("-")
                    if 0 <= int(start) <= len(CHAPTER_LINK_ELTS) - 1 and 0 <= int(end) <= len(CHAPTER_LINK_ELTS) - 1:
                        if not int(start) <= int(end):
                            r = None
                    else:
                        r = None

                new_range = r.group().split("-")
                CHAPTER_LINK_ELTS = CHAPTER_LINK_ELTS[int(new_range[0]):int(new_range[1]) + 1]

                print(f"\nWill download {len(CHAPTER_LINK_ELTS)} chapters.")
                time.sleep(2)

        #### CREATE A NEW FOLDER FOR THE MANGA ####
        print("\nChecking if Manga folder exists...")
        if os.path.isdir(Path(DOWNLOAD_FOLDER) / f'{manga_title}'):
            print("--> Found the download folder. Will download new chapters into it.")
        else:
            os.mkdir(DOWNLOAD_FOLDER / f'{manga_title}')
            print(f"Created a new folder {DOWNLOAD_FOLDER / f'{manga_title}'} and moved to it.")

        os.chdir(DOWNLOAD_FOLDER / f'{manga_title}')  # move to respective manga folder

        download_poster(manga_poster_link)

        ### MAKE HTML FOR MAIN PAGE ####
        chapter_website = open(manga_title + '.html', 'w')
        chapter_website.write(f'''<meta http-equiv="Refresh" content="0; url='{self.manga_page}'" />''')
        chapter_website.close()

        #### STORE MANGA INFO IN TXT FILE ####
        print("\nStored Manga details into text file.")
        empty_file = open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'w', encoding="utf-8")
        empty_file.close()
        with open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'a',
                  encoding="utf-8") as manga_info_file:
            manga_info_file.write(f"Manga: {manga_title}\n")
            manga_info_file.write(f"Status: {manga_status}\n")
            manga_info_file.write(f"Latest Chapter: {latest_chapter}\n")
            manga_info_file.write(f"Total Chapter Count: {len(CHAPTER_LINK_ELTS)}" + "\n")
            manga_info_file.write("\n" + f"Manga Site: {self.manga_page}")

        return manga_title, manga_status, latest_chapter, DOWNLOAD_FOLDER, CHAPTER_LINK_ELTS

    def download(self, download_details):

        manga_title = download_details[0]
        manga_status = download_details[1]
        latest_chapter = download_details[2]
        DOWNLOAD_FOLDER = download_details[3]
        CHAPTER_LINK_ELTS = download_details[4]

        if get_setting('CONFIRM BEFORE STARTING DOWNLOADS').upper() == 'YES':
            input("\nPress enter to start downloading...")

        print("\n----- STARTING DOWNLOADS -----")
        print("\nOpening Firefox...")

        try:
            browser = webdriver.Firefox(WEBDRIVER_LOCATION)
        except OSError:
            print("\nUh-oh looks like Selenium has trouble running on your OS. This script has been tested and works on Ubuntu 20, Windows 8.1 and Windows 10.")
            input('\nPress Enter to quit.')
            sys.exit()
        except:
            print("\nScript is having trouble opening up Firefox on your computer. Try the following:\n1. Make sure you have the latest version of Firefox installed.\n2. Check if the driver folder is in the same location as the .exe file or main.py and run the program again.")
            input('\nPress Enter to quit.')
            sys.exit()

        browser.implicitly_wait(10)

        count = 1
        newly_downloaded = []
        not_fully_downloaded = []
        already_downloaded = []

        for elt in CHAPTER_LINK_ELTS:
            os.chdir(DOWNLOAD_FOLDER / f'{manga_title}')  # move to respective manga folder
            print(f"\n##### Link {count} of {len(CHAPTER_LINK_ELTS)} #####")

            print("Opening", elt['href'], "...")
            browser.get(elt['href'])

            img_elts = browser.find_elements_by_xpath("//div[@class='container-chapter-reader']/img")

            print(f"Found {len(img_elts)} pages.")

            chapter_name = elt.text
            chapter_name = chapter_name.replace(":", " -").replace("?",
                                                                   "!").replace(
                '"', "'").replace("\\", "").replace("/", "").replace("|", "-or-").replace("*", "!").replace("<",
                                                                                                            "-less-than-").replace(
                ">", "-greater-than-").strip()

            # create respective chapter folder and move to it
            if chapter_name in os.listdir(os.getcwd()):
                print(f"--> Chapter folder '{chapter_name}' exists.")
            else:
                try:
                    os.mkdir(chapter_name)
                    print(f"Created a folder named '{chapter_name}' to download pages into.")
                except FileExistsError:
                    print(f"--> Chapter folder '{chapter_name}' exists.")
            os.chdir(chapter_name)

            # save webpage link in html to the chapter in the folder
            chapter_website = open(chapter_name + '.html', 'w')
            chapter_website.write(f'''<meta http-equiv="Refresh" content="0; url='{elt['href']}'" />''')
            chapter_website.close()

            if len(os.listdir(os.getcwd())) == len(img_elts) + 1:
                print("ALL IMAGE LINKS DOWNLOADED.")
                already_downloaded.append(chapter_name)
                count += 1
                continue

            print(f"DOWNLOADING {manga_title.upper()} {chapter_name.upper()}")

            # download images into that chapter folder
            for img in img_elts:
                if os.path.basename(img.get_attribute('src')) in os.listdir(os.getcwd()):
                    print(f"'{os.path.basename(img.get_attribute('src'))}' already downloaded.")
                    continue
                try:
                    if os.path.basename(img.get_attribute('src')).endswith(('.jpg', '.jpeg')):
                        print(f"Downloading '{os.path.basename(img.get_attribute('src')).replace('.jpg', '.png')}' ...")
                        img.screenshot(os.path.basename(img.get_attribute('src')).replace('.jpg', '.png'))
                    else:
                        print(f"Downloading '{os.path.basename(img.get_attribute('src'))}' ...")
                        img.screenshot(os.path.basename(img.get_attribute('src')))
                except:
                    print("!!!Unable to screenshot this image element. Will attempt to download it via requests.")
                    status = download_image(img.get_attribute('src'))
                    if status == 200:
                        # if image downloaded
                        im = Image.open(f"{os.path.basename(img.get_attribute('src'))}").convert("RGB")
                        im.save(os.path.basename(img.get_attribute('src')).replace('.jpg', '.png'), 'png')
                        send2trash.send2trash(os.path.basename(img.get_attribute('src')))
                    else:
                        print(f"!!!Unable to download image. Status Code:{status}. Link: {img.get_attribute('src')}")
                        print("Will screenshot the element again if possible.")
                        if os.path.basename(img.get_attribute('src')).endswith(('.jpg', '.jpeg')):
                            print(
                                f"Downloading '{os.path.basename(img.get_attribute('src')).replace('.jpg', '.png')}' ...")
                            img.screenshot(os.path.basename(img.get_attribute('src')).replace('.jpg', '.png'))
                        else:
                            print(f"Downloading '{os.path.basename(img.get_attribute('src'))}' ...")
                            img.screenshot(os.path.basename(img.get_attribute('src')))

            os.chdir(DOWNLOAD_FOLDER / f'{manga_title}')  # move back to respective manga folder
            print("DONE.")
            newly_downloaded.append(chapter_name)
            count += 1
        browser.close()
        print("\n----- DONE DOWNLOADING -----")

        print(f"\n{len(CHAPTER_LINK_ELTS)} total links found\n"
              f"{len(newly_downloaded)} newly downloaded chapters\n"
              f"{len(not_fully_downloaded)} chapters not fully downloaded\n"
              f"{len(already_downloaded)} chapters already downloaded")

        if len(not_fully_downloaded) != 0:
            print(f"\nWas not able to fully download the following {len(not_fully_downloaded)} chapters:")
            print('\n'.join(not_fully_downloaded))

            ##### update manga info in the text file
            empty_file = open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'w', encoding="utf-8")
            empty_file.close()
            with open(f"{manga_title.lower()} info (STATUS - {manga_status}).txt", 'a',
                      encoding="utf-8") as manga_info_file:
                manga_info_file.write(f"Manga: {manga_title}\n")
                manga_info_file.write(f"Status: {manga_status}\n")
                manga_info_file.write(f"Latest Chapter: {latest_chapter}\n")
                manga_info_file.write(f"Total Chapter Count: {len(CHAPTER_LINK_ELTS)}" + "\n")
                manga_info_file.write(
                    f"\nWas not able to fully download the following {len(not_fully_downloaded)} chapters:")
                manga_info_file.write("\n" + '\n'.join(not_fully_downloaded))
                manga_info_file.write("\n\n" + f"Manga Site: {self.manga_page}")
            os.rename(f"{manga_title.lower()} info (STATUS - {manga_status}).txt",
                      f"{manga_title.lower()} info (STATUS - ATTN REQUIRED).txt")
            print(f"\nUpdated manga details in '{manga_title.lower() + f' info (STATUS - ATTN REQUIRED).txt'}'.")
        
        os.system(f'start %windir%\\explorer.exe "{DOWNLOAD_FOLDER / manga_title}"')
