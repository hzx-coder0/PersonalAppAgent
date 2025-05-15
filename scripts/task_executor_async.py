import argparse
import ast
import datetime
import json
import os
import re
import sys
import time
import prompts
from config import load_config
from and_controller import list_all_devices, AndroidController, traverse_tree
from model import parse_explore_rsp, parse_grid_rsp, OpenAIModel, QwenModel
from utils import print_with_color, draw_bbox_multi, draw_grid
from datasets import load_dataset
import random
def load_local_dataset(data_files):
    # 数据集的后缀是.parquet
    if data_files.endswith(".parquet"):

        # 加载本地的 .parquet 数据集
        dataset = load_dataset('parquet', data_files=data_files, split='train')
    return dataset
async def task_executor_async(device, app, task_desc, root_dir="./"):

    persona_description = load_local_dataset("E:/temp/lab/ALL_Dataset/sher222___persona-iterative-responses/train-00000-of-00003.parquet")
    persona_description = persona_description["score_persona"]
    persona_description = [x['persona_description'] for x in persona_description]
    # 随机取两个persona
    seed = 100
    random.seed(seed)
    random.shuffle(persona_description)
    persona_description1 = persona_description[0:1]
    seed = 200
    random.seed(seed)
    random.shuffle(persona_description)
    persona_description2 = persona_description[0:1]
    persona_description = persona_description1 + persona_description2
    # buy = "I perfer to buy multicolor clothes, and I like to buy clothes with a discount. I wear size L."


    configs = load_config()

    if configs["MODEL"] == "OpenAI":
        mllm = OpenAIModel(base_url=configs["OPENAI_API_BASE"],
                        api_key=configs["OPENAI_API_KEY"],
                        model=configs["OPENAI_API_MODEL"],
                        temperature=configs["TEMPERATURE"],
                        max_tokens=configs["MAX_TOKENS"])
    elif configs["MODEL"] == "Qwen":
        mllm = QwenModel(api_key=configs["DASHSCOPE_API_KEY"],
                        model=configs["QWEN_MODEL"])
    else:
        print_with_color(f"ERROR: Unsupported model type {configs['MODEL']}!", "red")
        sys.exit()

    if not app:
        raise ValueError("ERROR: No app name provided!")
        
    app = app.replace(" ", "")
    app_dir = os.path.join(os.path.join(root_dir, "apps"), app)
    work_dir = os.path.join(root_dir, "tasks")
    if not os.path.exists(work_dir):
        os.mkdir(work_dir)
    auto_docs_dir = os.path.join(app_dir, "auto_docs")
    demo_docs_dir = os.path.join(app_dir, "demo_docs")
    task_timestamp = int(time.time())
    dir_name = datetime.datetime.fromtimestamp(task_timestamp).strftime(f"task_{app}_%Y-%m-%d_%H-%M-%S")
    task_dir = os.path.join(work_dir, dir_name)
    os.mkdir(task_dir)
    log_path = os.path.join(task_dir, f"log_{app}_{dir_name}.txt")

    no_doc = False
    if not os.path.exists(auto_docs_dir) and not os.path.exists(demo_docs_dir):
        print_with_color(f"No documentations found for the app {app}. Do you want to proceed with no docs? Enter y or n",
                        "red")
        user_input = ""
        while user_input != "y" and user_input != "n":
            user_input = input().lower()
        if user_input == "y":
            no_doc = True
        else:
            sys.exit()
    elif os.path.exists(auto_docs_dir) and os.path.exists(demo_docs_dir):
        print_with_color(f"The app {app} has documentations generated from both autonomous exploration and human "
                        f"demonstration. Which one do you want to use? Type 1 or 2.\n1. Autonomous exploration\n2. Human "
                        f"Demonstration",
                        "blue")
        user_input = ""
        while user_input != "1" and user_input != "2":
            user_input = input()
        if user_input == "1":
            docs_dir = auto_docs_dir
        else:
            docs_dir = demo_docs_dir
    elif os.path.exists(auto_docs_dir):
        print_with_color(f"Documentations generated from autonomous exploration were found for the app {app}. The doc base "
                        f"is selected automatically.", "yellow")
        docs_dir = auto_docs_dir
    else:
        print_with_color(f"Documentations generated from human demonstration were found for the app {app}. The doc base is "
                        f"selected automatically.", "yellow")
        docs_dir = demo_docs_dir

    controller = AndroidController(device)
    width, height = controller.get_device_size()
    if not width and not height:
        print_with_color("ERROR: Invalid device size!", "red")
        sys.exit()
    print_with_color(f"Screen resolution of {device}: {width}x{height}", "yellow")

    print_with_color(f"Starting instruction {task_desc} for {app} for device {device}", "yellow")
    

    round_count = 0
    last_act = "None"
    task_complete = False
    grid_on = False
    rows, cols = 0, 0


    def area_to_xy(area, subarea):
        area -= 1
        row, col = area // cols, area % cols
        x_0, y_0 = col * (width // cols), row * (height // rows)
        if subarea == "top-left":
            x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) // 4
        elif subarea == "top":
            x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) // 4
        elif subarea == "top-right":
            x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) // 4
        elif subarea == "left":
            x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) // 2
        elif subarea == "right":
            x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) // 2
        elif subarea == "bottom-left":
            x, y = x_0 + (width // cols) // 4, y_0 + (height // rows) * 3 // 4
        elif subarea == "bottom":
            x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) * 3 // 4
        elif subarea == "bottom-right":
            x, y = x_0 + (width // cols) * 3 // 4, y_0 + (height // rows) * 3 // 4
        else:
            x, y = x_0 + (width // cols) // 2, y_0 + (height // rows) // 2
        return x, y

    llast_act = []
    rsp = "None"
    while round_count < configs["MAX_ROUNDS"]:
        prompt = prompts.task_template
        prompt = re.sub(r"<user_description>", persona_description[0], prompt)
        round_count += 1
        print_with_color(f"Round {round_count}", "yellow")
        start = time.time()
        screenshot_path = controller.get_screenshot(f"{dir_name}_{round_count}", task_dir)
        xml_path = controller.get_xml(f"{dir_name}_{round_count}", task_dir)
        if screenshot_path == "ERROR" or xml_path == "ERROR":
            break
        if grid_on:
            rows, cols = draw_grid(screenshot_path, os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png"))
            image = os.path.join(task_dir, f"{dir_name}_{round_count}_grid.png")
            prompt = prompts.task_template_grid
        else:
            clickable_list = []
            focusable_list = []
            traverse_tree(xml_path, clickable_list, "clickable", True)
            traverse_tree(xml_path, focusable_list, "focusable", True)
            elem_list = clickable_list.copy()
            for elem in focusable_list:
                bbox = elem.bbox
                center = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
                close = False
                for e in clickable_list:
                    bbox = e.bbox
                    center_ = (bbox[0][0] + bbox[1][0]) // 2, (bbox[0][1] + bbox[1][1]) // 2
                    dist = (abs(center[0] - center_[0]) ** 2 + abs(center[1] - center_[1]) ** 2) ** 0.5
                    if dist <= configs["MIN_DIST"]:
                        close = True
                        break
                if not close:
                    elem_list.append(elem)
            draw_bbox_multi(screenshot_path, os.path.join(task_dir, f"{dir_name}_{round_count}_labeled.png"), elem_list,
                            dark_mode=configs["DARK_MODE"])
            image = os.path.join(task_dir, f"{dir_name}_{round_count}_labeled.png")
            if no_doc:
                prompt = re.sub(r"<ui_document>", "", prompt)
            else:
                ui_doc = ""
                for i, elem in enumerate(elem_list):
                    doc_path = os.path.join(docs_dir, f"{elem.uid}.txt")
                    if not os.path.exists(doc_path):
                        continue
                    ui_doc += f"Documentation of UI element labeled with the numeric tag '{i + 1}':\n"
                    doc_content = ast.literal_eval(open(doc_path, "r").read())
                    if doc_content["tap"]:
                        ui_doc += f"This UI element is clickable. {doc_content['tap']}\n\n"
                    if doc_content["text"]:
                        ui_doc += f"This UI element can receive text input. The text input is used for the following " \
                                f"purposes: {doc_content['text']}\n\n"
                    if doc_content["long_press"]:
                        ui_doc += f"This UI element is long clickable. {doc_content['long_press']}\n\n"
                    if doc_content["v_swipe"]:
                        ui_doc += f"This element can be swiped directly without tapping. You can swipe vertically on " \
                                f"this UI element. {doc_content['v_swipe']}\n\n"
                    if doc_content["h_swipe"]:
                        ui_doc += f"This element can be swiped directly without tapping. You can swipe horizontally on " \
                                f"this UI element. {doc_content['h_swipe']}\n\n"
                print_with_color(f"Documentations retrieved for the current interface:\n{ui_doc}", "magenta")
                ui_doc = """
                You also have access to the following documentations that describes the functionalities of UI 
                elements you can interact on the screen. These docs are crucial for you to determine the target of your 
                next action. You should always prioritize these documented elements for interaction:""" + ui_doc
                prompt = re.sub(r"<ui_document>", ui_doc, prompt)
        prompt = re.sub(r"<task_description>", task_desc, prompt)
        # 提取rsp中的Action和Summary
        
        if not rsp:
            rsp = "None"
            last_act = "None"
        else:
            match = re.search(r"Action:(.*?)(Summary:.*)", rsp, re.DOTALL)
            if match:
                action_content = match.group(1).strip()  # 提取 Action 后的内容
                summary_content = match.group(2).strip()  # 提取 Summary 及其后的内容
                last_act = f"Action: {action_content} {summary_content}"
        llast_act.append({"step": round_count - 1, "last_act": last_act})
        llast_act_str = json.dumps(llast_act, ensure_ascii=False)
        prompt = re.sub(r"<last_act>", llast_act_str, prompt)
        with open("prompt.txt", "w") as f:
            
            f.write(json.dumps({"step":round_count,"prompt": prompt})+"\n")
        print_with_color("Thinking about what to do in the next step...", "yellow")
        end = time.time()
        print_with_color(f"Time taken to process the screenshot and prompt: {end - start:.2f} seconds", "yellow")
        print("\n")
        start = time.time()
        rsp = ""
        async for partial_rsp in mllm.get_response_stream(prompt, [image]):
            rsp += partial_rsp
            yield rsp, partial_rsp
            
            
        print_with_color(rsp, "magenta")
        end = time.time()
        status = True
        print_with_color(f"Time taken to get response: {end - start:.2f} seconds", "yellow")
        print_with_color("Response received from the model:", "yellow")
        if status:
            with open(log_path, "a") as logfile:
                log_item = {"step": round_count, "prompt": prompt, "image": f"{dir_name}_{round_count}_labeled.png",
                            "response": rsp}
                logfile.write(json.dumps(log_item) + "\n")
            if grid_on:
                res = parse_grid_rsp(rsp)
            else:
                res = parse_explore_rsp(rsp)
            act_name = res[0]
            if act_name == "FINISH":
                task_complete = True
                break
            if act_name == "ERROR":
                break
            if act_name == "back":
                ret = controller.back()
                if ret == "ERROR":
                    print_with_color("ERROR: back execution failed", "red")
            if act_name == "home":
                ret = controller.home()
                if ret == "ERROR":
                    print_with_color("ERROR: home execution failed", "red")
            if act_name == "enter":
                ret = controller.enter()
                if ret == "ERROR":
                    print_with_color("ERROR: enter execution failed", "red")
            last_act = res[-1]
            res = res[:-1]
            if act_name == "tap":
                _, area = res
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                ret = controller.tap(x, y)
                if ret == "ERROR":
                    print_with_color("ERROR: tap execution failed", "red")
                    break
            elif act_name == "text":
                _, input_str = res
                ret = controller.text(input_str)
                if ret == "ERROR":
                    print_with_color("ERROR: text execution failed", "red")
                    break
            elif act_name == "long_press":
                _, area = res
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                ret = controller.long_press(x, y)
                if ret == "ERROR":
                    print_with_color("ERROR: long press execution failed", "red")
                    break
            elif act_name == "swipe":
                _, area, swipe_dir, dist = res
                tl, br = elem_list[area - 1].bbox
                x, y = (tl[0] + br[0]) // 2, (tl[1] + br[1]) // 2
                ret = controller.swipe(x, y, swipe_dir, dist)
                if ret == "ERROR":
                    print_with_color("ERROR: swipe execution failed", "red")
                    break
            elif act_name == "grid":
                grid_on = True
            elif act_name == "tap_grid" or act_name == "long_press_grid":
                _, area, subarea = res
                x, y = area_to_xy(area, subarea)
                if act_name == "tap_grid":
                    ret = controller.tap(x, y)
                    if ret == "ERROR":
                        print_with_color("ERROR: tap execution failed", "red")
                        break
                else:
                    ret = controller.long_press(x, y)
                    if ret == "ERROR":
                        print_with_color("ERROR: tap execution failed", "red")
                        break
            elif act_name == "swipe_grid":
                _, start_area, start_subarea, end_area, end_subarea = res
                start_x, start_y = area_to_xy(start_area, start_subarea)
                end_x, end_y = area_to_xy(end_area, end_subarea)
                ret = controller.swipe_precise((start_x, start_y), (end_x, end_y))
                if ret == "ERROR":
                    print_with_color("ERROR: tap execution failed", "red")
                    break
            if act_name != "grid":
                grid_on = False
            yield rsp, "the action has been executed"
            time.sleep(configs["REQUEST_INTERVAL"])
            
        else:
            print_with_color(rsp, "red")
            break
        

    if task_complete:
        print_with_color("Task completed successfully", "yellow")
    elif round_count == configs["MAX_ROUNDS"]:
        print_with_color("Task finished due to reaching max rounds", "yellow")
    else:
        print_with_color("Task finished unexpectedly", "red")
