import os,json
import time
from threading import Lock, Thread

from controller.BaseController import BaseController
from server.service.PlayBackService import PlayBackService
from myutils.configutils import get_user_folder
from myutils.jsonutils import getjson_path_byname


class TodoException(Exception):pass
class TodoExecuteException(Exception):pass

todo_runner_lock = Lock()
from mylogger.MyLogger3 import MyLogger
logger = MyLogger('todo_service')


class TodoService:
    _is_thread_todo_running = False

    def get_todo_by_name(self): pass

    @staticmethod
    def get_unrepeated_file(todo_json):
        # 提取非重复文件
        json_file_set = []
        for item in todo_json:
            enable = item.get('enable', False)
            # 只保留启用的清单
            if not enable: continue
            files = item.get('files', [])
            for file in files:
                if file not in json_file_set:
                    json_file_set.append(file)
        return json_file_set

    @staticmethod
    def _thread_todo_runner(todo_json=None):
        with todo_runner_lock:  # 子线程嵌套时，不要用同一个锁！

            if TodoService._is_thread_todo_running or PlayBackService.playing_thread_running:
                logger.error("已经有清单线程正在执行中，不要重复创建线程！")
                return
            try:
                if todo_json:
                    json_file_set = TodoService.get_unrepeated_file(todo_json)
                else:
                    todo_path = os.path.join(get_user_folder(), 'todo.json')
                    with open(todo_path, 'r', encoding='utf8') as f:
                        todo_dict = json.load(f)
                        json_file_set = TodoService.get_unrepeated_file(todo_dict)

                # 加载json并执行
                for json_file_name in json_file_set:
                    json_file_path = getjson_path_byname(json_file_name)
                    # socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'正在执行{json_file_name}')
                    if not os.path.exists(json_file_path):
                        # socket_emit(SOCKET_EVENT_PLAYBACK, msg=f'{json_file_name}不存在', success=False)
                        continue
                    while PlayBackService.playing_thread_running:
                        logger.debug(f'回放线程正在执行中，请等待')
                        time.sleep(1)
                        if not TodoService._is_thread_todo_running:
                            logger.debug("停止执行清单")
                            BaseController.stop_listen = True
                            return

                    with open(json_file_path, 'r', encoding='utf8') as f:
                        json_dict = json.load(f)
                    PlayBackService.playback_runner(json_dict)
            finally:
                TodoService._is_thread_todo_running = False
                logger.debug('结束执行清单了')
                # socket_emit(SOCKET_EVENT_PLAYBACK, msg='结束执行清单了')

    @staticmethod
    def todo_run(todo_json):
        # # 每次请求是不同的线程，意味着可能存在资源共享问题
        if not TodoService._is_thread_todo_running:
            files = TodoService.get_unrepeated_file(todo_json)
            if len(files) == 0:
                raise TodoExecuteException('空清单，无法执行')

            BaseController.stop_listen = False

            Thread(target=TodoService._thread_todo_runner, args=(todo_json,)).start()
            return True
        else:
            raise TodoExecuteException('已经有线程执行清单中')
            # return jsonify( {'success': False, 'status': PLAYBACK_STATUS_ALREADY_RUNNING, 'data': '已经有线程执行清单中'})

    @staticmethod
    def get_all_todos():
        todo_path = os.path.join(get_user_folder(), 'todo.json')
        if not os.path.exists(todo_path):
            with open(todo_path, 'w', encoding='utf8') as f:
                todo_dict = {'采集清单': {"enable": True, "files": []}}
                f.write(json.dumps(todo_dict))
            return todo_dict
        with open(todo_path, 'r', encoding='utf8') as f:
            try:
                data = json.load(f)
                return data
            except json.decoder.JSONDecodeError as e:
                raise TodoException('json解析错误！')

    @staticmethod
    def remove_none_exists_files():
        data = TodoService.get_all_todos()
        files_removed = []
        # 遍历所有的项目，检查文件路径是否存在，并移除不存在的文件
        for item in data:
            if "files" in item:
                original_files = item["files"]
                item["files"] = [f for f in original_files if os.path.exists(getjson_path_byname(f))]

                removed_files = set(original_files) - set(item["files"])
                if removed_files:
                    files_removed.append(removed_files)
                    logger.debug(f"Removed nonexistent files {removed_files} from {item['name']}")
        TodoService.save_todo(data)

    @staticmethod
    def todo_stop():
        BaseController.stop_listen = True
        if not TodoService._is_thread_todo_running:
            raise TodoExecuteException('未执行清单，无需停止')
        else:
            TodoService._is_thread_todo_running = False
            return True

    def remove_todo_by_name(self): pass

    @staticmethod
    def save_todo(data):
        todo_path = os.path.join(get_user_folder(), 'todo.json')
        with open(todo_path, 'w', encoding='utf8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
        return True

    @staticmethod
    def updateFileName(old_filename, new_filename):
        try:
            data = TodoService.get_all_todos()
            for item in data:
                item['files'] = [new_filename if file == old_filename else file for file in item['files']]

            # 将修改后的数据写回JSON文件
            TodoService.save_todo(data)
        except TodoException as e:
            raise TodoException(e)
        return True

    @staticmethod
    def removeFiles(files_to_remove):
        # 遍历所有的项目，寻找并移除指定文件
        data = TodoService.get_all_todos()
        # 遍历所有的项目，寻找并移除指定文件
        for item in data:
            if "files" in item:
                original_files = item["files"]
                item["files"] = [f for f in original_files if f not in files_to_remove]

                removed_files = set(original_files) - set(item["files"])
                if removed_files:
                    logger.debug(f"Removed {removed_files} from {item['name']}")

        TodoService.save_todo(data)

if __name__ == '__main__':
    # 定义要修改的文件名和新文件名
    # old_filename = "月莲_卡扎莱宫_须弥_5个.json"
    # new_filename = "月莲_卡扎莱宫_须弥_5个.json"
    # TodoService.updateFileName(old_filename, new_filename)

    # files_to_remove = [
    #     '月莲_禅那园_须弥_4个_20240814_113747.json',
    #     '丘丘萨满_千风神殿下_蒙德_1个_20240822_014632.json',
    #     '甜甜花1_测试_蒙德_0个_20240901_080854.json'
    #     # 添加更多要移除的文件名称
    # ]
    # TodoService.removeFiles(files_to_remove)
    data = TodoService.remove_none_exists_files()
    logger.debug(data)