import os
from git import Repo, Actor
from telegram.error import TelegramError
from uuid import uuid4

import config
from utils import text2jpg


class FileProcessor:

  repo = None
  repo_path_local = None
  files_path = None
  ssh_cmd = 'ssh'

  def __init__(self):
    if config.LINKS_REPO_DEPLOY_KEY:
      self.ssh_cmd = 'ssh -i ' + config.FILES_REPO_DEPLOY_KEY

    repo_path_local_base = ''
    if not config.FILES_REPO_PATH_LOCAL_ABS:
      repo_path_local_base = os.path.expanduser('~')
    self.repo_path_local = os.path.join(repo_path_local_base, config.FILES_REPO_PATH_LOCAL)
    self.repo = Repo.init(self.repo_path_local)
    try:
      self.repo.remotes.origin.exists()
      if self.repo.remotes.origin.url != config.FILES_REPO_URL:
        raise TelegramError('Links repository path seems to be conflicting with another repo')
    except AttributeError:
      self.repo.create_remote('origin', config.FILES_REPO_URL)
    with self.repo.git.custom_environment(GIT_SSH_COMMAND=self.ssh_cmd):
      self.repo.remotes.origin.pull(config.FILES_REPO_BRANCH)
    self.repo.git.checkout(config.FILES_REPO_BRANCH)

    # Init Shortener
    self.files_path = os.path.join(self.repo_path_local, 'docs')

  def git_pre(self):
    with self.repo.git.custom_environment(GIT_SSH_COMMAND=self.ssh_cmd):
      self.repo.remotes.origin.pull(config.FILES_REPO_BRANCH)

  def git_post(self):
    self.repo.git.add(A=True)
    author = Actor(config.FILES_REPO_AUTHOR_NAME, config.FILES_REPO_AUTHOR_EMAIL)
    self.repo.index.commit('Added url through deecubes_bot', author=author)
    with self.repo.git.custom_environment(GIT_SSH_COMMAND=self.ssh_cmd):
      self.repo.remotes.origin.push(config.FILES_REPO_BRANCH)

  def process_file(self, file_obj, file_name):
    # TODO: Remove telegram download method from here
    self.git_pre()
    file_path = os.path.join(self.files_path, file_name)
    if os.path.exists(file_path):
      file_name = str(uuid4()) + '-' + file_name
      file_path = os.path.join(self.files_path, file_name)

    # TODO: Add error handling for file io exceptions
    with open(file_path, 'wb') as out:
      file_obj.download(out=out)
    self.git_post()
    return config.FILES_BASE_URL + file_name

  def process_paste(self, content, file_name, make_image):
    if not file_name:
      file_name = str(uuid4())
      if make_image:
        file_name += '.png'
      else:
        file_name += '.txt'

    self.git_pre()
    file_path = os.path.join(self.files_path, file_name)
    if os.path.exists(file_path):
      file_name = str(uuid4()) + '-' + file_name
      file_path = os.path.join(self.files_path, file_name)

    if make_image:
      text2jpg(content, file_path)
    else:
      with open(file_path, 'w') as f:
        f.write(content)
    self.git_post()
    return config.FILES_BASE_URL + file_name
