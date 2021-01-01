from pathlib import Path
import os
import manga_sites

"""
Supported sites:
https://mangakakalot.com/
https://manganelo.com/manga/
https://m.manganelo.com
"""

PROGRAM_LOCATION = Path.cwd()
SUPPORTED_SITES = ' https://mangakakalot.com/ https://manganelo.com/manga/ https://m.manganelo.com'.split(' ')

os.environ['PATH'] += os.pathsep + str(PROGRAM_LOCATION / 'driver')  # set gecko driver location in path

### CHECK FOR SETTINGS.TXT FILE BEFORE STARTING ###
if 'settings.txt' not in os.listdir(PROGRAM_LOCATION):
    print(f"'settings.txt' file not found near program location ({PROGRAM_LOCATION}). Making a new settings.txt there...")

    with open(PROGRAM_LOCATION / 'settings.txt', 'w', encoding="UTF-8") as f:
        f.write('''DOWNLOADS DIRECTORY: DEFAULT\nDOWNLOAD ALL CHAPTERS: NO\nCONFIRM BEFORE STARTING DOWNLOADS: YES\n\nINFO\n- Setting download directory to DEFAULT creates a download folder where the exe file is.\n- DOWNLOAD ALL CHAPTERS specifes whether to download a range of chapters or to download all chapters found.\n- If invalid input is entered, default options will be used.''')


manga = str(input('\nEnter manga page link: '))

if 'https://mangakakalot.com/' in manga:
    bot = manga_sites.Mangakakalot(manga)
    details = bot.get_ready()
    bot.download(details)
elif 'manganelo.com/' in manga or 'https://m.manganelo.com' in manga:
    bot = manga_sites.Manganelo(manga)
    details = bot.get_ready()
    bot.download(details)
else:
    print("Looks like the link you put in is not currently supported :(\n"
          "\nCurrently supported sites:")
    print("\n".join(SUPPORTED_SITES))

input("\nPress Enter to quit.")




