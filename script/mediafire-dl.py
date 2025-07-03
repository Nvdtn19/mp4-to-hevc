#!/usr/bin/python

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
import sys
import os
import errno
import time

chunk_size = 1024 # 1KB
os_path_separator = os.path.sep

def make_sure_path_exists(path):
    try:
        os.makedirs(path)
    except OSError as exception:
        if exception.errno != errno.EEXIST:
            raise

class MediafireDownloader:
    dl_file_name = ''
    dl_file_full_path = ''
    dl_total_file_size = 0
    dl_existing_file_size = 0

    dl_page_url = ''
    dl_file_url = ''

    def __init__(self):
        pass

    def get_subfolders_from_folder(self, folder_key, parent):
        api_call_link = "http://mediafire.com/api/1.5/folder/get_content.php?folder_key=" + folder_key + \
                        "&content_type=folders&chunk_size=1000&response_format=json"
        resp_json = requests.get(api_call_link).json()
        subfolders_in_folder = resp_json['response']['folder_content']['folders']

        if not subfolders_in_folder:
            return False

        for subfolder in subfolders_in_folder:
            subfolder_name = subfolder['name']
            subfolder_parent = parent + subfolder_name + os_path_separator
            subfolder_key = subfolder['folderkey']

            print('----------------------------')
            print('Downloading folder: ' + subfolder_parent)
            self.download_folder(subfolder_key, subfolder_parent)

    def download_files_in_folder(self, folder_key, parent):
        api_call_link = "http://mediafire.com/api/1.5/folder/get_content.php?folder_key=" + folder_key \
                        + "&content_type=files&chunk_size=1000&response_format=json"
        resp_json = requests.get(api_call_link).json()
        files_in_folder = resp_json['response']['folder_content']['files']

        for file in files_in_folder:
            file_page_url = file['links']['normal_download']
            self.download_file(file_page_url, parent)

    def download_folder(self, folder_key, parent):
        self.download_files_in_folder(folder_key, parent)
        self.get_subfolders_from_folder(folder_key, parent)

    def download(self, mediafire_link):
        mediafire_folder_key = "mediafire.com/folder/"
        folder_slug_start = mediafire_link.find(mediafire_folder_key)
        
        if folder_slug_start == -1:
            self.download_file(mediafire_link, '')
        else:
            folder_slug_start += len(mediafire_folder_key)
            hash_pos = mediafire_link.rfind('#')
            
            if hash_pos != -1 and hash_pos > folder_slug_start:
                folder_key = mediafire_link[hash_pos+1:]
            else:
                folder_slug_end = mediafire_link.find('/', folder_slug_start)
                if folder_slug_end == -1:
                    folder_slug_end = len(mediafire_link)
                folder_key = mediafire_link[folder_slug_start:folder_slug_end]
            
            self.download_folder(folder_key, '')

    def download_file(self, mediafire_file_link, parent, file_name=''):
        cwd = os.getcwd()
        self.dl_page_url = mediafire_file_link
        print('----------------')
        print('Getting link from ' + self.dl_page_url)

        try:
            r_download_page = requests.get(self.dl_page_url)
            r_download_page.raise_for_status()
            soup_download_page = BeautifulSoup(r_download_page.text, 'lxml')
            download_link_element = soup_download_page.select_one('a.input.popsok')
            
            if not download_link_element or not download_link_element.get('href'):
                print(f"Could not find download button for {mediafire_file_link}. Skipping.")
                return

            self.dl_file_url = download_link_element['href']

            header_request = requests.head(self.dl_file_url, allow_redirects=True)
            self.dl_total_file_size = int(header_request.headers.get('Content-Length', 0))

            if file_name:
                self.dl_file_name = file_name
            else:
                cd = header_request.headers.get('content-disposition', '')
                file_name_key = 'filename="'
                fn_start = cd.find(file_name_key)
                if fn_start != -1:
                    fn_start += len(file_name_key)
                    fn_end = cd.find('"', fn_start)
                    self.dl_file_name = cd[fn_start:fn_end]
                else:
                    self.dl_file_name = os.path.basename(self.dl_file_url.split('?')[0])

            ss = os.path.join(cwd, parent)
            make_sure_path_exists(ss)
            self.dl_file_full_path = os.path.join(cwd, parent, self.dl_file_name)

            self.dl_existing_file_size = os.path.getsize(self.dl_file_full_path) if os.path.exists(self.dl_file_full_path) else 0

            if self.dl_existing_file_size >= self.dl_total_file_size and self.dl_total_file_size > 0:
                print(f'File "{os.path.join(parent, self.dl_file_name)}" already downloaded.')
                return

            print(f'Downloading "{self.dl_file_name}"...')
            headers = {'Range': f'bytes={self.dl_existing_file_size}-'}
            
            with requests.get(self.dl_file_url, headers=headers, stream=True) as r:
                r.raise_for_status()
                with open(self.dl_file_full_path, 'ab') as output_file:
                    with tqdm(total=self.dl_total_file_size, initial=self.dl_existing_file_size,
                              unit='B', unit_scale=True, desc=self.dl_file_name) as pbar:
                        for chunk in r.iter_content(chunk_size=chunk_size):
                            if chunk:
                                output_file.write(chunk)
                                pbar.update(len(chunk))
            
            print(f'\nFinished Downloading "{self.dl_file_full_path}".')

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

def main():
    if len(sys.argv) < 2:
        print('Usage: mediafire-dl.py mediafire_link_1 mediafire_link_2 ...')
        sys.exit(1)

    mf = MediafireDownloader()
    for mediafire_link in sys.argv[1:]:
        mf.download(mediafire_link)

if __name__ == "__main__":
    main()