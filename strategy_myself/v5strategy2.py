'''
这个文件是主要开发文件，涵盖了策略全部的四个接口
-on_event接收比赛状态变化的信息。
    参数event_type type表示事件类型；
    参数EventArgument表示该事件的参数，如果不含参数，则为NULL。
-get_team_info控制队名。
    修改返回值的字符串即可修改自己的队名
-get_instruction控制5个机器人的轮速(leftspeed,rightspeed)，以及最后的reset(1即表明需要reset)
    通过返回值来给机器人赋轮速
    比赛中的每拍被调用，需要策略指定轮速，相当于旧接口的Strategy。
    参数field为In/Out参数，存储当前赛场信息，并允许策略修改己方轮速。
    ！！！所有策略的开发应该在此模块
-get_placement控制5个机器人及球在需要摆位时的位置
    通过返回值来控制机器人和球的摆位。
    每次自动摆位时被调用，需要策略指定摆位信息。
    定位球类的摆位需要符合规则，否则会被重摆
'''
import random
from typing import Tuple, Union

from V5RPC import *
import math
from baseRobot import *
from GlobalVariable import *
baseRobots = []# 定义我方机器人数组
oppRobots = []# 定义对方机器人数组
data_loader = DataLoader()
race_state = -1  # 定位球状态
race_state_trigger = -1    # 触发方

tickBeginPenalty = 0
tickBeginGoalKick = 0
lastBallx = -110 + 37.5
lastBally = 0
BallPos = [Vector2(0, 0)] * 100000
resetHistoryRecord = False
newMatch = False

# 打印比赛状态，详细请对比v5rpc.py
@unbox_event
def on_event(event_type: int, args: EventArguments):
    event = {
        0: lambda: print(args.judge_result.reason),
        1: lambda: print("Match Start"),
        2: lambda: print("Match Stop"),
        3: lambda: print("First Half Start"),
        4: lambda: print("Second Half Start"),
        5: lambda: print("Overtime Start"),
        6: lambda: print("Penalty Shootout Start"),
        7: lambda: print("MatchShootOutStart"),
        8: lambda: print("MatchBlockStart")
    }
    global race_state_trigger
    global race_state
    if event_type == 0:
        race_state = args.judge_result.type
        race_state_trigger = args.judge_result.offensive_team
        if race_state == JudgeResultEvent.ResultType.PlaceKick:
            print("Place Kick")
        elif race_state == JudgeResultEvent.ResultType.PenaltyKick:
            print("Penalty Kick")
        elif race_state == JudgeResultEvent.ResultType.GoalKick:
            print("Goal Kick")
        elif (race_state == JudgeResultEvent.ResultType.FreeKickLeftBot
              or race_state == JudgeResultEvent.ResultType.FreeKickRightBot
              or race_state == JudgeResultEvent.ResultType.FreeKickLeftTop
              or race_state == JudgeResultEvent.ResultType.FreeKickRightTop):
            print("Free Kick")

        actor = {
            Team.Self: lambda: print("By Self"),
            Team.Opponent: lambda: print("By Opp"),
            Team.Nobody: lambda: print("By Nobody"),
        }
        actor[race_state_trigger]()

    event[event_type]()


@unbox_int
def get_team_info(server_version: int) -> str:
    version = {
        0: "V1.0",
        1: "V1.1"
    }
    print(f'server rpc version: {version.get(server_version, "V1.0")}')
    global newMatch
    newMatch = True
    return '一脚定乾坤'# 在此行修改双引号中的字符串为自己的队伍名

#*************************************常规策略**********************************
# 策略行为主函数，可将以下函数用策略模式封装
def strategy_common(field):
    # 最基本最常规情况下的执行策略
    # 假设黄方，给三个机器人限制活动范围

    football_now_x = field.ball.position.x
    football_now_y = field.ball.position.y
    futureBallx = 8 * football_now_x - 7 * BallPos[GlobalVariable.tick - 1].x
    futureBally = 8 * football_now_y - 7 * BallPos[GlobalVariable.tick - 1].y

    #1号机器人追球
    baseRobots[1].shoot(futureBallx, futureBally)
    #3号机器人在-30--20
    if futureBallx < -30:
        if futureBally < 0:
            baseRobots[3].moveto(-30, futureBally + 10)  # 3号机器人x不超过80的情况下追球（前锋）
        if futureBally > 0:
            baseRobots[3].moveto(-30, futureBally - 10)  # 3号机器人x不超过80的情况下追球（前锋）
    elif futureBallx > 20:
        baseRobots[3].moveto(20, futureBally)
    else:
        baseRobots[3].moveto(futureBallx, futureBally)  # 3号机器人x不超过80的情况下追球（前锋）
    # 2号机器人在0-60
    if futureBallx < 0:
        if futureBally < 0:
            baseRobots[2].moveto(0, futureBally + 10)  # 2号机器人x不超过-12的情况下追球（后卫）
        if futureBally > 0:
            baseRobots[2].moveto(0, futureBally - 10)  # 2号机器人x不超过-12的情况下追球（后卫）
    elif futureBallx < 75:
        if np.abs(futureBally) < 30:
            baseRobots[2].move_with_angle(futureBallx, futureBally, 0)
        else:
            if futureBally > 30:
                baseRobots[2].move_with_angle(futureBallx, futureBally, -45)
            if futureBally < -30:
                baseRobots[2].move_with_angle(futureBallx, futureBally, 45)
    else:
        baseRobots[2].moveto(75, futureBally)


    # 4号区域防守
    if np.abs(futureBally) < 47:
        baseRobots[4].moveto(-72.5, futureBally)
    elif futureBally > 47:
        baseRobots[4].moveto(futureBallx, 47)
        if baseRobots[4].get_pos().x > -75:
            baseRobots[4].moveto(-75, 47)
    elif futureBally < -47:
        baseRobots[4].moveto(futureBallx, -47)
        if baseRobots[4].get_pos().x > -75:
            baseRobots[4].moveto(-75, -47)

    # 防止有两个及以上球员处于球门区内
    if futureBallx < 0:
        for i in range(2, 5):
            if baseRobots[i].get_pos().x < -90 and np.fabs(baseRobots[i].get_pos().y) < 50:
                baseRobots[i].moveto(-90, baseRobots[i].get_pos().y)

    # 解决进攻冲撞守门员问题（1和4）
    if futureBallx > 100 and np.fabs(futureBally) < 30:
        baseRobots[1].moveto(95, futureBally)

    # 防止四人大禁区
    # 一旦大禁区里面有两个非门将球员，则其余就近出去，即使本来就在外面也无所谓，当防守了
    num_in_big_area = 0
    dis = [-1, -1, -1, -1, -1]  # -1 表示不在禁区里面
    for i in range(1, 5):
        if baseRobots[i].get_pos().x < -77 and np.fabs(baseRobots[i].get_pos().y) < 50:  # 禁区内机器人计数且计算距离，禁区外距离为负
            num_in_big_area += 1
            dis[i] = min(np.fabs(-72.5 - baseRobots[i].get_pos().x), np.fabs(np.fabs(baseRobots[i].get_pos().y) - 40))
    if num_in_big_area >= 2:
        out_robot1 = 1
        out_robot2 = 2
        for i in range(1, 5):
            if dis[i] < dis[out_robot1]:
                out_robot2 = out_robot1
                out_robot1 = i
            elif dis[i] < dis[out_robot2]:
                out_robot2 = i
        if dis[out_robot1] == np.fabs(baseRobots[out_robot1].get_pos().x + 72.5):
            baseRobots[out_robot1].moveto(-65, baseRobots[out_robot1].get_pos().y)
        elif np.fabs(baseRobots[out_robot1].get_pos().y > 0):
            baseRobots[out_robot1].moveto(baseRobots[out_robot1].get_pos().x, 50)
        else:
            baseRobots[out_robot1].moveto(baseRobots[out_robot1].get_pos().x, -50)

        if dis[out_robot2] == np.fabs(baseRobots[out_robot2].get_pos().x + 72.5):
            baseRobots[out_robot2].moveto(-65, baseRobots[out_robot2].get_pos().y)
        elif np.fabs(baseRobots[out_robot2].get_pos().y > 0):
            baseRobots[out_robot2].moveto(baseRobots[out_robot2].get_pos().x, 50)
        else:
            baseRobots[out_robot2].moveto(baseRobots[out_robot2].get_pos().x, -50)

    # 守门员策略
    if baseRobots[0].get_pos().x <= -110:
        baseRobots[0].moveto(-110 + 2, 0)
    else:
        if futureBallx < 0:
            if np.fabs(futureBally) < 30 - 0.7:
                if futureBallx > -110 + 30 or baseRobots[0].get_pos().x > -95:
                    baseRobots[0].moveto(-110 + 2, futureBally)
                else:
                    baseRobots[0].moveto(futureBallx, futureBally)
            elif np.fabs(futureBally) < 40 - 0.7:
                baseRobots[0].moveto(-110 + 2, 0)
            else:
                if futureBally > 40 and futureBallx < -75:
                    baseRobots[0].moveto(-110 + 2, 5)
                if futureBally > 40 and futureBallx > -75:
                    baseRobots[0].moveto(-110 + 2, 0)
                if futureBally < -40 and futureBallx < -75:
                    baseRobots[0].moveto(-110 + 2, -5)
                if futureBally < -40 and futureBallx > -75:
                    baseRobots[0].moveto(-110 + 2, 0)
        else:
            baseRobots[0].moveto(-110 + 2, 0)

    # 造犯规，我方防守，球在罚球区域，进攻方在球门区并且我方只有一个机器人在球门去(守门员)，让我方守门员撞他
    # 检查球是否在罚球区内
    if futureBallx < -75 and np.fabs(futureBally) < 40:
        for i in range(0, 5):
            # 获取进攻方机器人的位置
            opp_pos = oppRobots[i].get_pos()
            # 检查进攻方机器人是否在球门区内
            if opp_pos.x < -90 and np.fabs(opp_pos.y) < 30:
                # 获取守门员的位置
                baseRobots[0].moveto(opp_pos.x, opp_pos.y)


#************************************点球策略************************************
#设定初始策略为策略0
penalty_opt = 0
#********************************点球策略0***************************************
def strategy_penalty0(field):
    global tickBeginPenalty
    global race_state_trigger
    global penalty_opt 
    if race_state_trigger == Team.Self:
        for i in range(0, 5):
            baseRobots[i].set_wheel_velocity(0, 0)
        if GlobalVariable.tick - tickBeginPenalty <= 6:
            baseRobots[1].set_wheel_velocity(125, 125)#点球员推球
            baseRobots[2].set_wheel_velocity(125, 125)#
            baseRobots[3].set_wheel_velocity(115, 105)
            baseRobots[4].set_wheel_velocity(105, 115)
        elif GlobalVariable.tick - tickBeginPenalty <= 12:
            baseRobots[1].set_wheel_velocity(125, 125)#点球员推球
            baseRobots[2].set_wheel_velocity(125, 125)#
            baseRobots[3].set_wheel_velocity(115, 105)
            baseRobots[4].set_wheel_velocity(105, 115)
        elif GlobalVariable.tick - tickBeginPenalty <= 37:
            baseRobots[2].set_wheel_velocity(125, 125)#
            baseRobots[3].set_wheel_velocity(115, 105)
            baseRobots[4].set_wheel_velocity(105, 115)
        elif GlobalVariable.tick - tickBeginPenalty <= 50:
            baseRobots[2].set_wheel_velocity(-125, -125)#
            baseRobots[3].set_wheel_velocity(115, 105)
            baseRobots[4].set_wheel_velocity(105, 115)
        else:
            if GlobalVariable.tick - tickBeginPenalty == 66:
                if race_state_trigger == 0 and race_state == 2:
                    penalty_opt = (penalty_opt + 1) % 3
            strategy_common(field)
#**********************************点球策略1*************************************
def strategy_penalty1(field):
    global tickBeginGoalKick
    global race_state_trigger
    global penalty_opt
    football_now_x = field.ball.position.x
    football_now_y = field.ball.position.y
    futureBallx = 8 * football_now_x - 7 * BallPos[GlobalVariable.tick - 1].x
    futureBally = 8 * football_now_y - 7 * BallPos[GlobalVariable.tick - 1].y
    if race_state_trigger == Team.Self:
        for i in range(0, 5):
            baseRobots[i].set_wheel_velocity(0, 0)

        if  GlobalVariable.tick - tickBeginPenalty <= 12:
            baseRobots[1].set_wheel_velocity(50, 50)
        elif GlobalVariable.tick - tickBeginPenalty <= 22:
            baseRobots[1].set_wheel_velocity(50, 50)
            baseRobots[3].set_wheel_velocity(100, 100)
        elif GlobalVariable.tick -tickBeginPenalty <= 23:
            baseRobots[3].set_wheel_velocity(120, 120)
            baseRobots[1].set_wheel_velocity(-40, -50)
        elif GlobalVariable.tick - tickBeginPenalty <= 24:
            baseRobots[3].set_wheel_velocity(125, 125)#改3号
            baseRobots[2].set_wheel_velocity(115, 115)
        elif GlobalVariable.tick - tickBeginPenalty <= 32:
            baseRobots[3].set_wheel_velocity(125, 125)#改3号
        elif GlobalVariable.tick - tickBeginPenalty <= 35:
            baseRobots[3].set_wheel_velocity(125, 125)
        elif GlobalVariable.tick - tickBeginPenalty <= 58:
            baseRobots[3].set_wheel_velocity(-100, -95)
        else:
            if GlobalVariable.tick - tickBeginPenalty == 65:
                if race_state_trigger == 0 and race_state == 2:
                    penalty_opt = (penalty_opt + 1) % 3
            strategy_common(field)
        
#**********************************点球策略2************************************      
def strategy_penalty2(field):
    global tickBeginGoalKick
    global race_state_trigger
    global penalty_opt
    football_now_x = field.ball.position.x
    football_now_y = field.ball.position.y
    futureBallx = 8 * football_now_x - 7 * BallPos[GlobalVariable.tick - 1].x
    futureBally = 8 * football_now_y - 7 * BallPos[GlobalVariable.tick - 1].y
    if race_state_trigger == Team.Self:
        for i in range(0, 5):
            baseRobots[i].set_wheel_velocity(0, 0)
        if GlobalVariable.tick - tickBeginPenalty <= 33:
                baseRobots[1].set_wheel_velocity(125, -125)
                baseRobots[2].set_wheel_velocity(125, 125)
                baseRobots[3].set_wheel_velocity(-125,-125)
        elif GlobalVariable.tick - tickBeginPenalty <= 40:
                baseRobots[3].set_wheel_velocity(-125,-125)
        else:
            if GlobalVariable.tick - tickBeginPenalty == 64:
                if race_state_trigger == 0 and race_state == 2:
                    penalty_opt = (penalty_opt + 1) % 3
            strategy_common(field)

       
        
              

#*********************对方点球我方策略以及我方点球策略的选择************************
def strategy_penalty(field):
    global penalty_opt
    global tickBeginPenalty
    global race_state_trigger
    football_now_x = field.ball.position.x
    football_now_y = field.ball.position.y
    futureBallx = 4 * football_now_x - 3 * BallPos[GlobalVariable.tick - 1].x
    futureBally = 4 * football_now_y - 3 * BallPos[GlobalVariable.tick - 1].y
    if race_state_trigger ==Team.Self:
        if penalty_opt == 0:
            strategy_penalty0(field)
        if penalty_opt == 1:
            strategy_penalty1(field)
        if penalty_opt ==2:
            strategy_penalty2(field)
    if race_state_trigger == Team.Opponent:
        if GlobalVariable.tick - tickBeginPenalty <= 40 and football_now_x <= -70 and football_now_y <= 40:
            for i in range(0, 5):
                baseRobots[i].set_wheel_velocity(0, 0)
                baseRobots[3].set_wheel_velocity(105, 115)
                baseRobots[2].set_wheel_velocity(115, 105)
                baseRobots[0].moveto(futureBallx, futureBally)
        else:
            strategy_common(field)
#***********************************门球策略************************************

def strategy_goalkick(field):
    global tickBeginGoalKick
    global race_state_trigger
    if race_state_trigger == Team.Self:
        if GlobalVariable.tick - tickBeginGoalKick <= 40:
            for i in range(0, 5):
                baseRobots[i].set_wheel_velocity(0, 0)
            baseRobots[0].set_wheel_velocity(120, 120
                                             )
        else:
            strategy_common(field)
    if race_state_trigger == Team.Opponent:
        strategy_common(field)
        # python start.py 20001
#**********************************开球策略**************************************
def strategy_placeKick(field):
    global tickBeginPlace
    global race_state_trigger
    football_now_x = field.ball.position.x
    football_now_y = field.ball.position.y
    futureBallx = 8 * football_now_x - 7 * BallPos[GlobalVariable.tick - 1].x
    futureBally = 8 * football_now_y - 7 * BallPos[GlobalVariable.tick - 1].y
    if race_state_trigger == Team.Self:

        for i in range(0, 5):
            baseRobots[i].set_wheel_velocity(0, 0)
        baseRobots[1].turntoangle(180)
        if GlobalVariable.tick - tickBeginPlace <= 10:

            baseRobots[1].set_wheel_velocity(105, 105)
            baseRobots[3].set_wheel_velocity(125, 125)
        elif GlobalVariable.tick - tickBeginPlace <= 15:
            baseRobots[3].set_wheel_velocity(125, 125)
        elif GlobalVariable.tick - tickBeginPlace <= 35:
            baseRobots[3].set_wheel_velocity(125, 100)
        else:
            strategy_common(field)
    if race_state_trigger == Team.Opponent:
        strategy_common(field)



@unbox_field
def get_instruction(field: Field):
    # python start.py 20000    print(field.tick)  # tick从2起始
    GlobalVariable.tick = field.tick
    global resetHistoryRecord
    for i in range(0, 5):
        baseRobots.append(BaseRobot())
        oppRobots.append(BaseRobot())
        baseRobots[i].update(field.self_robots[i], resetHistoryRecord)
        oppRobots[i].update(field.opponent_robots[i], resetHistoryRecord)
        global newMatch
        if field.tick == 2: #newMatch is True:
            for j in range(0, 8):
                baseRobots[i].HistoryInformation[j] = field.self_robots[i].copy()   # 第0拍主动维护历史数据
                baseRobots[i].PredictInformation[j] = field.self_robots[i].copy()	# 第0拍主动维护预测数据
            newMatch = False
        baseRobots[i].PredictRobotInformation(4)#(GlobalVariable.tick_delay)

    football_now_x = -field.ball.position.x   # 黄方假设，球坐标取反
    football_now_y = -field.ball.position.y

    field.ball.position.x = -field.ball.position.x
    field.ball.position.y = -field.ball.position.y

    global BallPos
    BallPos[GlobalVariable.tick] = Vector2(football_now_x, football_now_y)
    if resetHistoryRecord is True:
        for i in range(GlobalVariable.tick, GlobalVariable.tick - 11, -1):
            BallPos[i] = Vector2(football_now_x, football_now_y)

    if race_state == JudgeResultEvent.ResultType.PenaltyKick:
        strategy_penalty(field)
    elif race_state == JudgeResultEvent.ResultType.GoalKick:
        strategy_goalkick(field)
    else:
        strategy_common(field)


    for i in range(0, 5):
        baseRobots[i].save_last_information(football_now_x, football_now_y)
    data_loader.set_tick_state(GlobalVariable.tick, race_state)
    resetHistoryRecord = False

    velocity_to_set = []
    for i in range(0, 5):
        velocity_to_set.append((baseRobots[i].robot.wheel.left_speed, baseRobots[i].robot.wheel.right_speed))

    return velocity_to_set, 0    # 以第二元素的(0,1)表明重置开关,1表示重置


@unbox_field
def get_placement(field: Field) -> List[Tuple[float, float, float]]:
    final_set_pos: List[Union[Tuple[int, int, int], Tuple[float, float, float]]]
    global resetHistoryRecord
    resetHistoryRecord = True
    if race_state == JudgeResultEvent.ResultType.PlaceKick:
        if race_state_trigger == Team.Self:
            print("开球进攻摆位")
            set_pos = [[-100, 20, 0],
                       [-6, -6, 45],
                       [-60, 0, 0],
                       [-15, 40, -35],
                       [-30, -30, 0],
                       [0.0, 0.0, 0.0]]
            # set_pos = [(-103, 0, 90), (30, 0, 0), (-3, -10, 0), (-3, 10, 0), (-3, 0, 0), (0.0, 0.0, 0.0)]
        else:   
            set_pos = [[-101, 0, 0],
                       [-50, 0, 0],
                       [-50, 40, 0],
                       [-50, -40, 0],
                       [-72, 0, 0],
                       [0.0, 0.0, 0.0]]
            # set_pos = [(-105, 0, 90), (10, 20, -90), (10, -20, -90), (10, 40, -90), (10, -40, -90), (0.0, 0.0, 0.0)]
    elif race_state == JudgeResultEvent.ResultType.PenaltyKick:
        global tickBeginPenalty
        tickBeginPenalty = field.tick
        if race_state_trigger == Team.Self:
            if penalty_opt ==  0:
                print("点球进攻摆位0")
                set_pos = [[-95, 0, 0],#守门员0
                        [73.5, -5, 130],#点球员1
                        [-10, 90, -45],#二射2
                        [-10, 50, 0],#3
                        [-10, -50, 0],#4用于球被踢回时及时防守
                        [5, 10.0, 0.0]]
            elif penalty_opt == 1:
                print("点球进攻摆位1")
                set_pos = [[-95, 0, 0],
                          [69.5, -5.5, 135],#点球员不改
                          [-5, -30, -35],#2二次击球
                          [-5, -7, 0],#3
                          [-10, 30, -20],
                          [5, 10.0, 0.0]]
            elif penalty_opt == 2:
                print("点球进攻摆位2")
                set_pos = [[-95, 0, 0],#0
                          [73.5, 5.5, 135],#点球员1
                          [-10, -55, 30],#2
                          [-5, 20, 90],#3
                          [-10, 70, 0],
                          [5, 10.0, 0.0]]

        else:  
            print("点球防守摆位")
            set_pos = [[-110, 0, 0],#守门员0
                       [10, 20, -110],#1
                       [5, 40, -180],#2
                       [5, -40, -180],#3
                       [10, 20, -180],#4
                       [0, 0.0, 0.0]]
    elif race_state == JudgeResultEvent.ResultType.GoalKick:
        global tickBeginGoalKick
        tickBeginGoalKick = field.tick
        if race_state_trigger == Team.Self:
            print("门球进攻摆位")
            set_pos = [[-101-1, 0, 73],
                       [-110+60, 40, -90],
                       [-50, -40, -90],
                       [-30, 0, -90],
                       [-50, 0, -90],
                       [-95.27, 9.05, 0.0]]
        else:   # if race_state_trigger == Team.Opponent:
            print("门球防守摆位")
            set_pos = [[-105, 0, 0],
                       [30, 0, 0],
                       [-30, -10, 0],
                       [-50, 10, 0],
                       [-80, 0, 0],
                       [0.0, 0.0, 0.0]]
    elif (race_state == JudgeResultEvent.ResultType.FreeKickLeftTop
          or race_state == JudgeResultEvent.ResultType.FreeKickRightTop
          or race_state == JudgeResultEvent.ResultType.FreeKickRightBot
          or race_state == JudgeResultEvent.ResultType.FreeKickLeftBot):
        if race_state_trigger == Team.Self:
            print("争球进攻摆位")
            set_pos = [[-103, 0, 90],
                       [30, 0, 0],
                       [-3, -10, 0],
                       [-3, 10, 0],
                       [-3, 0, 0],
                       [0.0, 0.0, 0.0]]
        else:   # if race_state_trigger == Team.Opponent:
            print("争球防守摆位")
            set_pos = [[-105, 0, 0],
                       [30, 0, 0],
                       [10, -10, 0],
                       [10, 10, 0],
                       [10, 0, 0],
                       [0.0, 0.0, 0.0]]
    else:
        print("race_state = " + str(race_state))

    for set_pos_s in set_pos:     # 摆位反转
        set_pos_s[0] = -set_pos_s[0]
        set_pos_s[1] = -set_pos_s[1]
        set_pos_s[2] -= 180
        if set_pos_s[2] < -180:
            set_pos_s[2] += 360
    final_set_pos = [(set_pos[0][0], set_pos[0][1], set_pos[0][2]),
                     (set_pos[1][0], set_pos[1][1], set_pos[1][2]),
                     (set_pos[2][0], set_pos[2][1], set_pos[2][2]),
                     (set_pos[3][0], set_pos[3][1], set_pos[3][2]),
                     (set_pos[4][0], set_pos[4][1], set_pos[4][2]),
                     (set_pos[5][0], set_pos[5][1], set_pos[5][2])]

    print(final_set_pos)
    return final_set_pos  # 最后一个是球位置（x,y,角）,角其实没用