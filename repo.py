import tempfile
from dataclasses import dataclass
import logging
import os
from enum import Enum
from novalapp import _, get_app
from novalapp.common.encodings import UTF8_FILE_ENCODING
from novalapp.util import fileutils
from novalapp.executable import Executable
from novalapp.util import strutils
from .exceptions import ProjectNotRepositoryError
from .cmd import GitCmd
log = logging.getLogger(__name__)


class RepofileState(Enum):
    FILE_MODIFIED_STAGED = 1
    FILE_MODIFIED_UNSTAGED = 2
    FILE_DELETED_STAGED = 3
    FILE_DELETED_UNSTAGED = 4
    FILE_UNTRACKED = 5
    FILE_NEW_STAGED = 6
    FILE_UNMERGE_MODIFIED = 7
    FILE_UNMERGE_DELETED = 8


@dataclass
class CommitFile:
    filepath: str
    file_state: int
    fullpath: str


UNKWNOW_BRANCH_NAME = 'Unkwnow branch'


class Repo:
    """description of class"""

    COMMIT_ID_FLAG = 'commit '
    # 执行add命令时,允许一次添加的最大文件数量
    MAX_ADD_FILES = 100
    # 执行add命令时,超过此文件数量时接收输出需要使用大容量输出文件,而不是用进程管道
    MAX_ADD_PIPE_FILES = 20

    def __init__(self, repo_path):
        self._git = GitCmd(repo_path)

    @property
    def git(self):
        return self._git

    @property
    def repo_path(self):
        return self._git.work_path

    @staticmethod
    def short_file_list(files):
        new_files = []
        filename_length = 0
        max_filename_length = Executable.MAX_COMMAND_LINE_LENGTH - 100
        for filename in files:
            if filename_length > max_filename_length:
                log.warning(
                    "commit total %d files short to %d files, files length %d exceed max file length %d",
                    len(files),
                    len(new_files),
                    filename_length,
                    max_filename_length
                )
                new_files.pop()
                break
            new_files.append(filename)
            filename_length += len(filename)
            filename_length += 1
        return new_files

    @classmethod
    def filelist_to_args(cls, file_list):
        new_files = []
        file_count = 0
        for i, filepath in enumerate(file_list):
            if i <= cls.MAX_ADD_FILES:
                new_files.append(strutils.emphasis_path(filepath))
                file_count = i
            else:
                log.warning(
                    'add file %s exceed max limit add files count %d',
                    filepath,
                    cls.MAX_ADD_FILES
                )
        new_short_filelist = cls.short_file_list(new_files)
        file_path_args = ' '.join(new_short_filelist)
        return file_path_args, file_count

    def remote_addrs(self):
        addr_dct = {}
        output = self._git.call_output("remote -v")
        for line in output.splitlines():
            splits = line.split()
            addr = splits[1]
            name = splits[0]
            addr_dct[name] = addr
        return addr_dct

    def filepath_to_abspath(self, filepath):
        fullpath = os.path.abspath(os.path.join(self._git.work_path, filepath))
        return fullpath

    def status(self, commit_file_path=None):

        def is_commit_file(commit_file_path, status_file_path):
            if commit_file_path is not None and not fileutils.ComparePath(
                commit_file_path, status_file_path
            ):
                return False
            return True

        modify_flag = 'modified:'
        delete_flag = 'deleted:'
        new_file_flag = 'new file:'
        rename_flag = 'renamed:'
        unmerged_both_add_flag = 'both added:'
        unmerged_both_modify_flag = 'both modified:'
        unmerged_delete_by_us_flag = 'deleted by us:'
        unmerged_delete_by_them_flag = 'deleted by them:'
        has_unmerged = False

        commit_file_list = []
        file_state = -1

        for line in self._git.huge_output_call('status'):
            linestr = self._git.bytes_to_str_detect_encoding(line, raw_unicode_escape=True)
            # 加入待提交状态的修改文件
            if linestr.find('Changes to be committed:') != -1:
                file_state = RepofileState.FILE_MODIFIED_STAGED
                continue
            # 已修改但未加入待提交状态的文件
            if linestr.find('Changes not staged for commit:') != -1:
                file_state = RepofileState.FILE_MODIFIED_UNSTAGED
                continue
            # 加入merge冲突后待提交状态的修改文件
            if linestr.find('Unmerged paths:') != -1:
                file_state = RepofileState.FILE_UNMERGE_MODIFIED
                has_unmerged = True
                continue

            if file_state in [
                RepofileState.FILE_MODIFIED_STAGED,
                RepofileState.FILE_MODIFIED_UNSTAGED
            ] and linestr.find(modify_flag) != -1:
                filepath = linestr.replace(modify_flag, "").strip()
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                commit_file_list.append(CommitFile(filepath, file_state, fullpath))

            elif file_state == RepofileState.FILE_UNMERGE_MODIFIED and (
                linestr.find(unmerged_both_add_flag) != -1
            ):
                filepath = linestr.replace(unmerged_both_add_flag, "").strip()
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                commit_file_list.append(CommitFile(filepath, file_state, fullpath))

            elif file_state == RepofileState.FILE_UNMERGE_MODIFIED and (
                linestr.find(unmerged_both_modify_flag) != -1
            ):
                filepath = linestr.replace(unmerged_both_modify_flag, "").strip()
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                commit_file_list.append(CommitFile(filepath, file_state, fullpath))

            elif linestr.find(unmerged_delete_by_us_flag) != -1:
                filepath = linestr.replace(unmerged_delete_by_us_flag, "").strip()
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                commit_file_list.append(
                    CommitFile(filepath, RepofileState.FILE_UNMERGE_DELETED, fullpath)
                )

            elif linestr.find(unmerged_delete_by_them_flag) != -1:
                filepath = linestr.replace(unmerged_delete_by_them_flag, "").strip()
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                commit_file_list.append(
                    CommitFile(filepath, RepofileState.FILE_UNMERGE_DELETED, fullpath)
                )

            elif linestr.find(new_file_flag) != -1:
                filepath = linestr.replace(new_file_flag, "").strip()
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                commit_file_list.append(
                    CommitFile(filepath, RepofileState.FILE_NEW_STAGED, fullpath)
                )

            elif linestr.find(rename_flag) != -1:
                filestr = linestr.replace(rename_flag, "").strip()
                paths = filestr.split('->')
                staged_remove_file_path = paths[0].strip()
                staged_new_file_path = paths[1].strip()
                log.debug("file %s renamed to %s", staged_remove_file_path, staged_new_file_path)
                full_staged_remove_file_path = self.filepath_to_abspath(staged_remove_file_path)
                full_staged_new_file_path = self.filepath_to_abspath(staged_new_file_path)
                if not is_commit_file(commit_file_path, full_staged_new_file_path) or (
                    not is_commit_file(commit_file_path, full_staged_remove_file_path)
                ):
                    continue
                commit_file_list.append(CommitFile(
                    staged_remove_file_path,
                    RepofileState.FILE_DELETED_STAGED,
                    full_staged_remove_file_path
                ))
                commit_file_list.append(CommitFile(staged_new_file_path,
                                        RepofileState.FILE_NEW_STAGED, full_staged_new_file_path))

            elif linestr.find(delete_flag) != -1:
                filepath = linestr.replace(delete_flag, "").strip()
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                if file_state == RepofileState.FILE_MODIFIED_STAGED:
                    commit_file_list.append(
                        CommitFile(filepath, RepofileState.FILE_DELETED_STAGED, fullpath)
                    )

                elif file_state == RepofileState.FILE_MODIFIED_UNSTAGED:
                    commit_file_list.append(
                        CommitFile(filepath, RepofileState.FILE_DELETED_UNSTAGED, fullpath)
                    )

            # git未追踪的文件
            elif linestr.find('Untracked files:') != -1:
                file_state = RepofileState.FILE_UNTRACKED

            elif file_state == RepofileState.FILE_UNTRACKED and linestr.find('git add <file>...') == -1 and (
                linestr.find('no changes added to commit') == -1 and linestr.find('nothing added to commit') == -1
            ):
                filepath = linestr.strip()
                if filepath == "":
                    continue
                fullpath = self.filepath_to_abspath(filepath)
                if not is_commit_file(commit_file_path, fullpath):
                    continue
                commit_file_list.append(
                    CommitFile(filepath, RepofileState.FILE_UNTRACKED, fullpath)
                )

        return has_unmerged, commit_file_list

    def add(self, file_path):
        full_path = file_path
        if not os.path.isabs(file_path):
            full_path = os.path.join(self.repo_path, file_path).rstrip("/").rstrip(os.sep)
        if os.path.isdir(full_path):
            files = []
            add_file_count = 0
            file_dir = full_path.replace(self.repo_path, "").lstrip(os.sep)
            for file in os.listdir(full_path):
                relpath = file_dir + os.sep + file
                if not os.path.isdir(os.path.join(self.repo_path, relpath)):
                    files.append(relpath)
                    add_file_count += 1
            log.warning(
                'add file path %s is dir, list dir all files count is %d',
                full_path,
                add_file_count
            )
            self.add_files(files)
        else:
            self.add_files([file_path])

    def branchs(self):
        branch_list = []
        current_index = -1
        output, returncode = self._git.call("branch")
        if returncode != 0 and output.lower().find('fatal: not a git repository') != -1:
            raise ProjectNotRepositoryError(_('fatal: not a git repository'))
        else:
            for i, line in enumerate(output.splitlines()):
                if line.find('*') != -1:
                    branch_list.append(line.lstrip('*').strip())
                    current_index = i
                else:
                    branch_list.append(line.strip())
        return branch_list, current_index

    def branch(self):
        branch_list, current_index = self.branchs()
        if current_index == -1:
            return UNKWNOW_BRANCH_NAME
        return branch_list[current_index]

    def checkout(self, branch_or_filename):
        self._git.call_output(f"checkout {branch_or_filename}")

    def tags(self):
        output = self._git.call_output('tag')
        return output.strip().splitlines()

    def new_tag(self, name, msg, commit_id=None):
        tag_msg = "\"%s\"" % (msg)
        tag_cmd = f'tag -a {name} -m {tag_msg}'
        if commit_id is not None:
            tag_cmd += " "
            tag_cmd += commit_id
        self._git.call_output(tag_cmd)

    def push_tag(self, tagname, addr):
        self._git.call_output(f'push {addr} {tagname}')

    def delete_tag(self, tagname):
        self._git.call_output(f'tag -d {tagname}')

    def remove(self, file_path, delete=False):
        file_path = strutils.emphasis_path(file_path)
        if delete:
            self._git.call_output(f"rm {file_path} -f")
        else:
            self._git.call_output(f"rm {file_path} --cached")

    def checkout_new_branch(self, branch_name):
        self._git.call_output(f"checkout -b {branch_name}")

    def checkout_remote_branch(self, branch_name):
        self._git.call_output(f"checkout -b {branch_name} origin/{branch_name}")

    def commit(self, msg):
        self.commit_files(msg)

    def commit_files(self, msg, amend=False):
        temp_handle, temp_fn = tempfile.mkstemp(
            suffix=".txt",
            prefix="%s_git_" % get_app().GetAppName()
        )
        log.info("temp file path of commit text is:%s", temp_fn)
        with os.fdopen(temp_handle, "w", encoding=UTF8_FILE_ENCODING) as f:
            f.write(msg)
        if not amend:
            self._git.call_output(f"commit -F {temp_fn}")
        else:
            self._git.call_output(f"commit --amend -F {temp_fn}")

    def push(self, branch_name):
        self._git.call_output(f"push origin {branch_name}")

    def add_files(self, file_list):
        file_path_args, file_count = self.filelist_to_args(file_list)
        git_add_cmd = f"add {file_path_args}"
        if file_count < self.MAX_ADD_PIPE_FILES:
            self._git.call_output(git_add_cmd)
        else:
            for line in self._git.huge_output_call(git_add_cmd):
                log.warning(str(line))

    def logs(self, branch=None, top_n=None):
        '''
        获取分支最近n次提交的commit id
        '''
        commit_ids = []
        command = 'log'
        if branch is not None:
            command += f' {branch}'
        if top_n is not None:
            command += f' -n {top_n}'
        output = self._git.call_output(command)
        for line in output.splitlines():
            if line.find(self.COMMIT_ID_FLAG) != -1:
                commit_id = line.replace(self.COMMIT_ID_FLAG, "").strip()
                commit_ids.append(commit_id)
        return commit_ids

    def list_status_files(self, commit_id, fullpath=False):
        '''
        获取某次提交的新增/修改文件列表
        '''
        changed_files = []
        output = self._git.call_output(f'show --pretty="" --name-status {commit_id}')
        for line in output.splitlines():
            if line.startswith('M') or line.startswith('A'):
                filename = line[1:].strip()
                if fullpath:
                    normal_fullpath = fileutils.opj(
                        os.path.join(self.repo_path, filename)
                    )
                    changed_files.append(normal_fullpath)
                else:
                    changed_files.append(filename)
        return changed_files
