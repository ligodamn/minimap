import time

# 委托流程：
# 已知委托的地点都是固定的

# 保存委托
# 把所有的委托全部存起来，用json文件存放

from BasePathExecutor2 import BasePathExecutor,Point, BasePath
import os,cv2
import numpy as np
from typing import List
import json
from capture.capture_factory import capture
from matchmap.minimap_interface import MinimapInterface
from mylogger.MyLogger3 import MyLogger
logger = MyLogger("daily_mission_executor")

# 纯战斗

# 邪恶的扩张 消灭所有魔物 0/8 0/5
# 持盾的危机 消灭所有魔物 0/5
# 邱邱人的一小步 消灭所有魔物0/8
# [为了执行官大人!] 击败所有敌人 0/3
# 圆滚滚的易爆品 消灭所有魔物 0/8
# 临危受命 消灭丘丘霜凯王 0/1 蒙德-覆雪之路

# 破坏
# 攀高危险 摧毁邱邱人哨塔

# 对话
# [冒险家]的能力极限 帮助赫尔曼先生
# 鸽子习惯一去不回 帮助杜拉夫先生 0/1
# 语言交流


class UnfinishedException(Exception): pass  # 只录制了一半的委托

class DailyMissionPoint(Point):
    DAILY_MISSION_TYPE_SKIP_DIALOG = 'dialog'
    DAILY_MISSION_TYPE_FIGHT = 'fight'
    DAILY_MISSION_TYPE_DESTROY_TOWER = 'destroy_tower'

    EVENT_FIGHT = 'fight'
    EVENT_DESTROY = 'destroy'
    EVENT_DIALOG = 'dialog'
    EVENT_FIND_NPC = 'find_npc'
    EVENT_COLLECT = 'collect'
    EVENT_CLIMB = 'climb'  # 爬神像，做不到

    def __init__(self, x, y, type=Point.TYPE_PATH, move_mode=Point.MOVE_MODE_NORMAL, action=None, events=None):
        super().__init__(x=x,y=y,type=type,move_mode=move_mode,action=action)
        self.events = events

class DailyMissionPath(BasePath):
    def __init__(self, name, country, positions: List[DailyMissionPoint], anchor_name=None, enable=None):
        super().__init__(name=name, country=country, positions=positions, anchor_name=anchor_name)
        self.enable=enable

class DailyMissionPathExecutor(BasePathExecutor):
    def __init__(self, json_file_path, debug_enable=None):
        super().__init__(json_file_path=json_file_path, debug_enable=debug_enable)

    @staticmethod
    def load_basepath_from_json_file(json_file_path) -> DailyMissionPath:
        with open(json_file_path, encoding="utf-8") as r:
            json_dict = json.load(r)
            points: List[DailyMissionPoint] = []
            for point in json_dict.get('positions', []):
                p = DailyMissionPoint(x=point.get('x'),
                          y=point.get('y'),
                          type=point.get('type', Point.TYPE_PATH),
                          move_mode=point.get('move_mode', Point.MOVE_MODE_NORMAL),
                          action=point.get('action'),events=point.get('events'))
                points.append(p)
            return DailyMissionPath(
                name=json_dict['name'], country=json_dict['country'], positions=points,
                enable=json_dict.get('enable', True)  # 未记录完成的委托标记为False
            )

    # @staticmethod
    # def scale_down():
    #     import win32api, win32con
    #     import time
    #     delta = -5000
    #     for _ in range(20):
    #         win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
    #         time.sleep(0.02)  # 短暂等待，防止事件过于密集

    # 1. 按下m，然后滚轮向下把视野放大。
    # @staticmethod
    # def scroll_down_for_looking_more_locations():
    #     DailyMissionPathExecutor.scale_down()

    # 2. 模板匹配查找屏幕中的所有的任务的坐标
    @staticmethod
    def find_all_mission_from_screen():
        from myutils.configutils import resource_path
        # 传送锚点流程
        # 加载地图位置检测器
        template_image = cv2.imread(os.path.join(resource_path, "template", "icon_mission.jpg"))
        gray_template = cv2.cvtColor(template_image, cv2.COLOR_BGR2GRAY)

        original_image = capture.get_screenshot().copy()
        gray_original = cv2.cvtColor(original_image, cv2.COLOR_BGR2GRAY)

        # 获取模板图像的宽度和高度
        w, h = gray_template.shape[::-1]

        # 将小图作为模板，在大图上进行匹配
        result = cv2.matchTemplate(gray_original, gray_template, cv2.TM_CCOEFF_NORMED)

        # 设定阈值
        threshold = 0.85
        # 获取匹配位置
        locations = np.where(result >= threshold)

        mission_screen_points = []
        prev_point = None
        # 绘制匹配结果
        from myutils.executor_utils import euclidean_distance
        for pt in zip(*locations[::-1]):
            center_x = pt[0] + w // 2
            center_y = pt[1] + h // 2
            if prev_point is None:
                prev_point = pt
                mission_screen_points.append((center_x, center_y))

            elif euclidean_distance(prev_point, pt) > 10:
                mission_screen_points.append((center_x, center_y))
                prev_point = pt

            cv2.rectangle(original_image, pt, (pt[0] + w, pt[1] + h), (0, 255, 0), 2)

        # 显示结果
        original_image = cv2.resize(original_image, None, fx=0.5, fy=0.5)
        # cv2.imshow('Matched Image', original_image)
        # cv2.waitKey(20)
        # if key == ord('q'):
        #     cv2.destroyAllWindows()
        return mission_screen_points
    # 3. 请求一次屏幕中心的世界坐标，和当前缩放
    # 4. 2和3的结果做运算，得到实际坐标

    @staticmethod
    def get_world_missions(missions_screen_points):
        user_map_position = MinimapInterface.get_user_map_position()
        w,h = capture.w, capture.h
        mission_world_points = []
        for mission_screen_point in missions_screen_points:
            scale = MinimapInterface.get_user_map_scale()
            if user_map_position and scale:
                dx = mission_screen_point[0] - w/2
                dy = mission_screen_point[1] - h/2
                world_x = user_map_position[0] + dx/scale[0]
                world_y = user_map_position[1] + dy/scale[1]
                mission_world_points.append((world_x,world_y))
        return mission_world_points

    @staticmethod
    def search_closest_mission_json(target_point):
        """
        查找指定位置最近的委托
        :param target_point:
        :return:
        """
        if target_point is None:
            raise Exception("目标点不能为空")
        from myutils.executor_utils import euclidean_distance
        from myutils.configutils import resource_path
        mission_path = os.path.join(resource_path, 'pathlist', '委托')

        closet_mission_json = None
        min_distance = None
        for mission_file_name in os.listdir(mission_path):
            with open(os.path.join(mission_path, mission_file_name), encoding='utf-8') as f:
                dme = json.load(f)
                mission_point = dme.get('positions')[-1]
                d = euclidean_distance(target_point, (mission_point['x'], mission_point['y']))
                if min_distance is None:
                    min_distance = d
                    closet_mission_json = os.path.join(mission_path, mission_file_name)
                    continue

                if min_distance > d:
                    min_distance = d
                    closet_mission_json = os.path.join(mission_path, mission_file_name)
        return closet_mission_json

    # 5. 遍历实际坐标，遍历所有已存放的委托列表, 查找最近的一个委托
    @staticmethod
    def execute_all_mission():

        # 模板匹配屏幕中出现的委托,得到他们的屏幕坐标
        missions_screen_points = DailyMissionPathExecutor.find_all_mission_from_screen()
        # 计算得到世界坐标
        mission_world_points = DailyMissionPathExecutor.get_world_missions(missions_screen_points)

        # 5. 执行委托
        for mission_world_point in mission_world_points:
            closest = DailyMissionPathExecutor.search_closest_mission_json(mission_world_point)
            print(closest)
            try:
                DailyMissionPathExecutor(closest).execute()
            except UnfinishedException as e:
                logger.error(e)
                continue


    def on_execute_before(self):
        self.base_path: DailyMissionPath
        if not self.base_path.enable:
            raise UnfinishedException("未完成路线，跳过")
        super().on_execute_before()

    def wait_until_wipe_out(self):
        start_time = time.time()
        while time.time()-start_time < 25:
            time.sleep(1)
            self.log(f"正在检测委托是否完成, 剩余{25-(time.time()-start_time)}秒")
            if self.ocr.find_match_text('委托完成'):
                break
    def wait_until_destroy(self):
        start_time = time.time()
        while time.time()-start_time < 20:
            time.sleep(1)
            self.log(f"正在检测委托是否完成, 剩余{20-(time.time()-start_time)}秒")
            if self.ocr.find_match_text('委托完成'):
                break

    def wait_until_dialog_finished(self):
        start = time.time()
        while time.time()-start < 30:
            self.log(f"正在等待对话结束, 剩余等待时间{30-(time.time()-start)}")
            if capture.has_paimon():
                self.log("发现派蒙，对话结束")
                break
            time.sleep(1)

    def on_move_after(self, point: DailyMissionPoint):
        super().on_move_after(point)
        if point.type == DailyMissionPoint.TYPE_TARGET:
            for event in point.events:
                event_type = event.get("type")
                if event_type == DailyMissionPoint.EVENT_FIGHT:
                    self.log("战斗!")
                    self.kb_press_and_release('`')
                    self.wait_until_wipe_out()
                    self.kb_press_and_release('`')
                elif event_type == DailyMissionPoint.EVENT_DESTROY:
                    self.log("破坏柱子!")
                    self.kb_press_and_release('`')
                    self.wait_until_destroy()
                    self.kb_press_and_release('`')
                elif event_type == DailyMissionPoint.EVENT_FIND_NPC:
                    self.log("查找npc")
                    time.sleep(1)
                    self.kb_press_and_release('f')
                    time.sleep(1)
                elif event_type == DailyMissionPoint.EVENT_DIALOG:
                    self.log("对话")
                    self.wait_until_dialog_finished()
                else:
                    self.log(f"暂时无法处理{event_type}类型的委托")



# 1. 按下m，然后滚轮向下把视野放大。
# 2. 模板匹配查找屏幕中的所有的任务相对于屏幕中心的坐标
# 3. 请求一次屏幕中心的世界坐标，和当前缩放
# 4. 2和3的结果做运算，得到实际坐标
# 5. 遍历实际坐标，遍历所有已存放的委托列表, 查找最近的一个委托
# 5. 执行委托

if __name__ == '__main__':
    # pos = (1282.2781718749993, -5754.44564453125)
    from controller.MapController2 import MapController
    mp = MapController()
    time.sleep(2)
    mp.kb_press_and_release('m')
    time.sleep(1)
    time.sleep(0.5)
    mp.choose_country('蒙德')
    mp.zoom_out(-5000)
    mp.zoom_out(-5000)
    mp.zoom_out(-5000)
    time.sleep(0.5)
    DailyMissionPathExecutor.execute_all_mission()

