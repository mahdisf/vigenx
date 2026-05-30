from twich_video_downloader import get_video_entries

url = 'https://www.twitch.tv/directory/category/counter-strike/clips?range=7d'

print(get_video_entries(url))