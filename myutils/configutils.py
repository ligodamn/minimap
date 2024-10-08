import os
# 创建 YAML 对象，保留注释
from ruamel.yaml import YAML
yaml = YAML()
yaml.preserve_quotes = True

# 一个实例对应一个配置，包括todo.json和config.yaml，其余相同

import sys
# config_name = 'config.yaml'
application_path = '.'
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
    application_path = os.path.join(application_path, '_internal')
elif __file__:
    application_path = os.path.dirname(os.path.dirname(__file__))

PROJECT_PATH = application_path
resource_path = os.path.join(PROJECT_PATH, 'resources')

class BaseConfig:
    _yaml_obj = None
    # _yaml_file = "config.dev.yaml"  # 给子类继承
    current_instance_name = 'instance1'
    _yaml_file = f'config-{current_instance_name}.yaml'  # 默认
    @classmethod
    def get_yaml_file(cls): return cls._yaml_file

    # template
    _yaml_template_obj = None
    _yaml_template_file = 'config-template.yaml'

    @classmethod
    def get_user_folder(cls):
        """
        获取当前实例用户目录
        :return:
        """
        user_folder = os.path.join(resource_path, f'user-{cls.current_instance_name}')
        if not os.path.exists(user_folder):
            user_template = os.path.join(resource_path, 'user-template')
            import shutil
            shutil.copytree(user_template, user_folder)
        return user_folder

    # @classmethod
    # def _create_instance_file(cls):
    #     account_yaml_path = os.path.join(PROJECT_PATH, 'account.yaml')
    #     account = YAML()
    #     with open(account_yaml_path, 'r', encoding='utf8') as f:
    #         instances = account.load(f)
    #     import shutil
    #     yaml_template_file = os.path.join(PROJECT_PATH,cls._yaml_template_file)
    #     if not os.path.exists(yaml_template_file): raise Exception("config-template.yaml模板配置文件丢失!")
    #     for key in instances.keys():
    #         config_instance_path = os.path.join(PROJECT_PATH, f'config-{key}.yaml')
    #         print(config_instance_path)
    #         if not os.path.exists(config_instance_path):
    #             shutil.copy(yaml_template_file, config_instance_path)
    @classmethod
    def get_instances(cls):
        account_yaml_path = os.path.join(PROJECT_PATH, 'account.yaml')
        account = YAML()
        with open(account_yaml_path, 'r', encoding='utf8') as f:
            instances = account.load(f)
            return instances

    @classmethod
    def set_instance(cls, instance_name):
        """
        设置指定的实例
        :param instance_name:
        :return:
        """
        if instance_name is None:
            instance_name = 'instance1'
        cls.current_instance_name = instance_name
        cls._yaml_file = f'config-{instance_name}.yaml'
        cls.reload_config()

        ins = BaseConfig.get_instances()
        ins['current_instance'] = instance_name
        with open(os.path.join(PROJECT_PATH, 'account.yaml'), 'w', encoding='utf8') as f:
            yaml.dump(ins, f)


    @classmethod
    def _load_if_none(cls):
        if cls._yaml_obj is None:
            cls.reload_config()

    @classmethod
    def get_yaml_object(cls, is_template=False):
        cls._load_if_none()
        if is_template:
            return cls._yaml_template_obj
        return cls._yaml_obj

    @classmethod
    def get(cls,key, default=None, min_val=None, max_val=None):
        value = cls.get_yaml_object().get(key, default)
        if value is None and cls._yaml_template_obj is not None:
            value = cls._yaml_template_obj.get(key, default)

        if min_val is not None and max_val is not None:
            if value < min_val: value = min_val
            elif value > max_val: value = max_val
        return value

    @classmethod
    def set(cls, key, value):
        cls.get_yaml_object()[key] = value

    @classmethod
    def save_config(cls):
        yaml_file = os.path.join(PROJECT_PATH, cls._yaml_file)
        with open(yaml_file, "w", encoding="utf8") as f:
            yaml.dump(cls.get_yaml_object(), f)

    @classmethod
    def reload_config(cls):
        yaml_file = os.path.join(PROJECT_PATH, cls._yaml_file)
        yaml_template_file = os.path.join(PROJECT_PATH, cls._yaml_template_file)
        if not os.path.exists(yaml_template_file):
            raise Exception("config-template.yaml模板配置文件丢失!")

        # 如果文件不存在则创建实例
        if not os.path.exists(yaml_file):
            import shutil
            shutil.copy(yaml_template_file, yaml_file)

        with open(yaml_file, 'r', encoding='utf8') as f:
            cls._yaml_obj = yaml.load(f)

        with open(yaml_template_file, 'r', encoding='utf8') as f:
            cls._yaml_template_obj = yaml.load(f)


# 一定要先运行一次，让BaseConfig._yaml_obj不为None，否则其子类都不会继承BaseConfig的_yaml_obj，导致他们的数据不相同
BaseConfig.reload_config()

class MapConfig(BaseConfig):
    _yaml_obj = None
    _yaml_file = 'config.map.yaml'

    @staticmethod
    def get_all_map():
        return MapConfig.get_yaml_object()


class DebugConfig(BaseConfig):
    KEY_DEBUG_ENABLE = 'debug_enable'

class WindowsConfig(BaseConfig):
    KEY_WINDOW_NAME = 'window_name'

class PathExecutorConfig(BaseConfig):
    KEY_LOCAL_MAP_SIZE = 'local_map_size'  # 允许范围512 ~ 4096 # 越大越卡
    KEY_SHOW_PATH_VIEWER = 'show_path_viewer'  # 跑点位的时候是否展示路径
    KEY_PATH_VIEWER_WIDTH = 'path_viewer_width'  # 路径展示的宽高，允许范围(50~4096
    KEY_ENABLE_CRAZY_F = 'enable_crazy_f'  # 自动拾取开关(没有做ocr，仅是在接近点位的时候疯狂按下f)
    KEY_MOVE_NEXT_POINT_ALLOW_MAX_TIME = 'move_next_point_allow_max_time'  # 移动到下一个点位最大允许时间（秒），超过该时间则跳过该点位, 允许范围(5~60)
    KEY_STUCK_MOVEMENT_THRESHOLD = 'stuck_movement_threshold'  # 8秒内移动的总距离(像素)在多少范围内认为卡住，允许范围(2~50)
    KEY_TARGET_NEARBY_THRESHOLD = 'target_nearby_threshold'  # 对于目标点精确到多少个像素认为接近, 允许范围(1~10)
    KEY_PATH_POINT_NEARBY_THRESHOLD = 'path_point_nearby_threshold'  # 对于途径点精确到多少个像素认为接近, 允许范围(2~50)
    KEY_ALLOW_SMALL_STEPS = 'allow_small_steps'  # 是否允许小碎步接近目标：注意此选项对途径点以及游泳模式下无效
    KEY_ENABLE_FOOD_REVIVE = 'enable_food_revive'  # 死亡后，是否允许使用道具复苏角色
    KEY_ENABLE_LOOP_PRESS_E = 'enable_loop_press_e'  # 跑路的时候不断按下按键(e技能)，0表示关闭,1表示开启
    KEY_ENABLE_LOOP_PRESS_Z = 'enable_loop_press_z'  # 跑路时不断按下z，0表示关闭,1表示开启
    KEY_ENABLE_LOOP_JUMP = 'enable_loop_jump'  # 是否允许循环跳跃，0表示关闭,1表示开启
    KEY_LOOP_PRESS_E_INTERVAL = 'loop_press_e_interval'  # 循环按下e的时间间隔
    KEY_SMALL_STEP_INTERVAL = 'small_step_interval'  # 小碎步按下w的频率，允许范围(0.05~0.2)
    KEY_ENABLE_DASH = 'enable_dash'  # 是否允许途径点冲刺
    KEY_CHANGE_ROTATION_MAX_SPEED = 'change_rotation_max_speed'  # 转向速度，允许范围200~1000
    KEY_UPDATE_USER_STATUS_INTERVAL = 'update_user_status_interval'  # 多少秒更新一次位置，允许值0.01~0.2
    KEY_POSITION_MUTATION_THRESHOLD = 'position_mutation_threshold'  # 当前位置和历史点位差距超过多少认为位置突变，允许范围(50-200)
    KEY_POSITION_MUTATION_MAX_TIME = 'position_mutation_max_time'  # 一段路径中允许位置突变次数，允许范围(0~10)
    KEY_SEARCH_CLOSEST_POINT_MAX_DISTANCE = 'search_closet_point_max_distance'  # 路径突变后搜索最近点位策略，允许范围(80~500)

class FightConfig(BaseConfig):
    KEY_DEFAULT_FIGHT_TEAM = 'default_fight_team'
    KEY_FIGHT_TIMEOUT = 'fight_duration'

class DailyMissionConfig(BaseConfig):
    KEY_DAILY_TASK_FIGHT_TEAM = 'daily_task_fight_team'
    KEY_DAILY_TASK_EXECUTE_TIMEOUT = 'daily_task_execute_timeout'
    KEY_DAILY_TASK_FIGHT_TIMEOUT = 'daily_task_fight_timeout'
    KEY_DAILY_TASK_DESTROY_TIMEOUT = 'daily_task_destroy_timeout'
    KEY_DAILY_TASK_KAISELIN = 'daily_task_kaiselin'

class LeyLineConfig(BaseConfig):
    KEY_LEYLINE_TYPE = 'leyline_type'
    KEY_LEYLINE_OUTCROP_TASK_EXECUTE_TIMEOUT = 'leyline_outcrop_task_execute_timeout'
    KEY_LEYLINE_OUTCROP_TASK_FIGHT_TIMEOUT = 'leyline_outcrop_task_fight_timeout'
    KEY_LEYLINE_ENABLE_WANYE_PICKUP_AFTER_REWARD = 'leyline_enable_wanye_pickup_after_reward'
    KEY_LEYLINE_FIGHT_TEAM = 'leyline_fight_team'


class ServerConfig(BaseConfig):
    KEY_HOST = 'host'
    KEY_PORT = 'port'

def reload_config():
    BaseConfig.reload_config()

# def get_user_folder():
#     user_folder = os.path.join(resource_path, 'user')
#     if not os.path.exists(user_folder):
#         user_template = os.path.join(resource_path, 'user-template')
#         import shutil
#         shutil.copytree(user_template, user_folder)
#     return user_folder
# BaseConfig._create_instance_file()

if __name__ == '__main__':
    print(BaseConfig.get_yaml_object() == FightConfig.get_yaml_object())
    BaseConfig.set_instance("instance2")
    BaseConfig.reload_config()
    print(FightConfig.get_yaml_file())
    print(BaseConfig.get_user_folder())
    # print(BaseConfig.get_instances())
    # BaseConfig.set_instance('instance2')
    # print(LeyLineConfig.get(LeyLineConfig.KEY_LEYLINE_TYPE))