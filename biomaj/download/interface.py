import os
import logging
import datetime
import time
import re
import tarfile
import zipfile

from biomaj.utils import Utils

from biomaj.mongo_connector import MongoConnector


class DownloadInterface:
  '''
  Main interface that all downloaders must extend
  '''

  files_num_threads = 4

  def __init__(self):
    self.files_to_download = []
    self.files_to_copy = []
    self.error = False
    self.credentials = None
    #bank name
    self.bank = None


  def set_progress(self, val, max):
    '''
    Update progress on download

    :param val: number of downloaded files since last progress
    :type val: int
    :param max: number of files to download
    :type max: int
    '''
    logging.debug('Download:progress:'+str(val)+'/'+str(max))
    if not self.bank:
      logging.debug('bank not specified, skipping record of download progress')
      return

    MongoConnector.banks.update({'name': self.bank},{'$inc': {'status.download.progress': val}, '$set': {'status.download.total': max}})

  def match(self, patterns, file_list, dir_list=[], prefix=''):
    '''
    Find files matching patterns. Sets instance variable files_to_download.

    :param patterns: regexps to match
    :type patterns: list
    :param file_list: list of files to match
    :type file_list: list
    :param dir_list: sub directories in current dir
    :type dir_list: list
    :param prefix: directory prefix
    :type prefix: str
    '''
    logging.debug('Download:File:RegExp:'+str(patterns))
    self.files_to_download = []
    for pattern in patterns:
      subdirs_pattern = pattern.split('/')
      if len(subdirs_pattern) > 1:
        # Pattern contains sub directories
        subdir = subdirs_pattern[0]
        if subdir == '^':
          subdirs_pattern = subdirs_pattern[1:]
          subdir = subdirs_pattern[0]
        logging.debug('Download:File:Subdir:Check:'+subdir)
        if re.match(subdirs_pattern[0], subdir):
          logging.debug('Download:File:Subdir:Match:'+subdir)
          # subdir match the beginning of the pattern
          # check match in subdir
          (subfile_list, subdirs_list) = self.list(prefix+'/'+subdir+'/')
          self.match(['/'.join(subdirs_pattern[1:])], subfile_list, subdirs_list, prefix+'/'+subdir)

      else:
        for rfile in file_list:
          if re.match(pattern, rfile['name']):
            rfile['root'] = self.rootdir
            if prefix != '':
              rfile['name'] = prefix + '/' +rfile['name']
            self.files_to_download.append(rfile)
            logging.debug('Download:File:MatchRegExp:'+rfile['name'])
    if len(self.files_to_download) == 0:
      raise Exception('no file found matching expressions')



  def set_permissions(self, file_path, file_info):
    '''
    Sets file attributes to remote ones
    '''
    ftime = datetime.date(int(file_info['year']),int(file_info['month']),int(file_info['day']))
    settime = time.mktime(ftime.timetuple())
    os.utime(file_path, (settime, settime))

  def download_or_copy(self, available_files, root_dir, check_exists=True):
    '''
    If a file to download is available in available_files, copy it instead of downloading it.

    Update the instance variables files_to_download and files_to_copy

    :param available_files: list of files available in root_dir
    :type available files: list
    :param root_dir: directory where files are available
    :type root_dir: str
    :param check_exists: checks if file exists locally
    :type check_exists: bool
    '''

    self.files_to_copy = []
    available_files.sort(key=lambda x: x['name'])
    self.files_to_download.sort(key=lambda x: x['name'])

    new_files_to_download = []

    test1_tuples = ((d['name'], d['year'], d['month'], d['day'], d['size']) for d in self.files_to_download)
    test2_tuples = set((d['name'], d['year'], d['month'], d['day'], d['size']) for d in available_files)
    new_or_modified_files = [t for t in test1_tuples if t not in test2_tuples]
    index = 0

    if len(new_or_modified_files) > 0:
      for file in self.files_to_download:
        if index < len(new_or_modified_files) and \
          file['name'] == new_or_modified_files[index][0]:
          new_files_to_download.append(file)
          index += 1
        else:
          if not check_exists or os.path.exists(os.path.join(root_dir,file['name'])):
            file['root'] = root_dir
            self.files_to_copy.append(file)
          else:
            new_files_to_download.append(file)

    else:
      # Copy everything
      for file in self.files_to_download:
        if not check_exists or os.path.exists(os.path.join(root_dir,file['name'])):
          file['root'] = root_dir
          self.files_to_copy.apppend(file)
        else:
          new_files_to_download.append(file)

    self.files_to_download = new_files_to_download


  def download(self, local_dir):
    '''
    Download remote files to local_dir

    :param local_dir: Directory where files should be downloaded
    :type local_dir: str
    :return: list of downloaded files
    '''
    pass

  def list(self):
    '''
    List directory

    :return: tuple of file list and dir list
    '''
    pass

  def chroot(self, cwd):
    '''
    Change directory
    '''
    pass

  def set_credentials(userpwd):
    '''
    Set credentials in format user:pwd

    :param userpwd: credentials
    :type userpwd: str
    '''
    self.credentials = userpwd

  def close(self):
    '''
    Close connection
    '''
    pass
