import re
from abc import abstractmethod
from typing import List
from http import HTTPStatus

import requests
import dashscope

from utils import print_with_color, encode_image

import json
from openai import OpenAI, OpenAIError, RateLimitError, AsyncOpenAI
from httpcore import RemoteProtocolError
import time
import gradio as gr
from typing import List, Any, Iterator
class BaseModel:
    def __init__(self):
        pass

    @abstractmethod
    def get_model_response(self, prompt: str, images: List[str]):
        pass


class OpenAIModel(BaseModel):
    def __init__(self, base_url: str, api_key: str, model: str, temperature: float, max_tokens: int):
        super().__init__()
        self.base_url = base_url
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    def get_model_response(self, prompt: str, images: List[str]):
        content = [
            {
                "type": "text",
                "text": prompt
            }
        ]
        for img in images:
            base64_img = encode_image(img)
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{base64_img}"
                }
            })
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens
        }

        mllm = OpenAI(api_key=self.api_key, base_url=self.base_url)

        # 发送请求并检查响应
        retries = 0
        flag = True
        while retries < 5 and flag:
            try:
                response = mllm.chat.completions.create(**payload)
                response_json = response.to_dict()  # 将响应转换为字典
                flag = False
                # response_json = response.json()
            except requests.exceptions.RequestException as e:
                print_with_color(f"HTTP request error: {e}", "red")
                return False, str(e)
            except json.JSONDecodeError as e:
                print_with_color(f"JSON decode error: {e}", "red")
                print_with_color(f"Response content: {response.text}", "red")
                retries += 1
            # 如果openai达到了请求限制，延时一段时间后重试
            except RateLimitError as e:
                print_with_color(f"Rate limit error: {e}", "red")
                time.sleep(30)
                retries += 1
            except OpenAIError as e:
                print_with_color(f"OpenAI error: {e}", "red")
                time.sleep(30)
                retries += 1
            except RemoteProtocolError as e:
                print_with_color(f"Remote protocol error: {e}", "red")
                time.sleep(20)
                retries += 1
            if retries > 0:
                print_with_color(f"Retry {retries} times", "magenta")

            

        # response = requests.post(self.base_url, headers=headers, json=payload).json()
        if "error" not in response_json:
            usage = response_json["usage"]
            prompt_tokens = usage["prompt_tokens"]
            completion_tokens = usage["completion_tokens"]
            print_with_color(f"Request cost is "
                             f"${'{0:.2f}'.format(prompt_tokens / 1000 * 0.01 + completion_tokens / 1000 * 0.03)}",
                            "yellow")
        else:
            return False, response_json["error"]["message"]
        return True, response_json["choices"][0]["message"]["content"]

    async def get_response_stream(self, prompt: str, images: List[str]):
            """流式输出OpenAI响应"""
            content = [
            {
                "type": "text",
                "text": prompt
            }
            ]
            for img in images:
                base64_img = encode_image(img)
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_img}"
                    }
                })
            payload = {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "stream": True  # 开启流式输出
            }
            
            # 调用OpenAI API进行流式输出 (新版API)
            mllm = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)

            # 发送请求并检查响应
            retries = 0
            flag = True
            response =await mllm.chat.completions.create(**payload)
            # create variables to collect the stream of chunks
            # iterate through the stream of events
            # response_json = response.to_dict()  # 将响应转换为字典
            full_response = ""
            
            async for chunk in response:
                content = chunk.choices[0].delta.content
                if content:
                    yield content

    def clear_history():
        """清除聊天历史记录"""
        return []
class QwenModel(BaseModel):
    def __init__(self, api_key: str, model: str):
        super().__init__()
        self.model = model
        dashscope.api_key = api_key

    def get_model_response(self, prompt: str, images: List[str]) :
        content = [{
            "text": prompt
        }]
        for img in images:
            img_path = f"file://{img}"
            content.append({
                "image": img_path
            })
        messages = [
            {
                "role": "user",
                "content": content
            }
        ]
        response = dashscope.MultiModalConversation.call(model=self.model, messages=messages)
        if response.status_code == HTTPStatus.OK:
            return True, response.output.choices[0].message.content[0]["text"]
        else:
            return False, response.message


def parse_explore_rsp(rsp):
    try:
        observation = re.findall(r"Observation: (.*?)$", rsp, re.MULTILINE)[0]
        think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        act = re.findall(r"Action: (.*?)$", rsp, re.MULTILINE)[0]
        last_act = re.findall(r"Summary: (.*?)$", rsp, re.MULTILINE)[0]
        print_with_color("Observation:", "yellow")
        print_with_color(observation, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        print_with_color("Action:", "yellow")
        print_with_color(act, "magenta")
        print_with_color("Summary:", "yellow")
        print_with_color(last_act, "magenta")
        if "FINISH" in act:
            return ["FINISH"]
        act_name = act.split("(")[0]
        if act_name == "back" or act_name == "home" or act_name == "enter":
            return [act_name, last_act]
        if act_name == "tap":
            area = int(re.findall(r"tap\((.*?)\)", act)[0])
            return [act_name, area, last_act]
        elif act_name == "text":
            input_str = re.findall(r"text\((.*?)\)", act)[0][1:-1]
            return [act_name, input_str, last_act]
        elif act_name == "long_press":
            area = int(re.findall(r"long_press\((.*?)\)", act)[0])
            return [act_name, area, last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0]
            area, swipe_dir, dist = params.split(",")
            area = int(area)
            swipe_dir = swipe_dir.strip()[1:-1]
            dist = dist.strip()[1:-1]
            return [act_name, area, swipe_dir, dist, last_act]
        elif act_name == "grid":
            return [act_name]
        else:
            print_with_color(f"ERROR: Undefined act {act_name}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the model response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


def parse_grid_rsp(rsp):
    try:
        observation = re.findall(r"Observation: (.*?)$", rsp, re.MULTILINE)[0]
        think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        act = re.findall(r"Action: (.*?)$", rsp, re.MULTILINE)[0]
        last_act = re.findall(r"Summary: (.*?)$", rsp, re.MULTILINE)[0]
        print_with_color("Observation:", "yellow")
        print_with_color(observation, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        print_with_color("Action:", "yellow")
        print_with_color(act, "magenta")
        print_with_color("Summary:", "yellow")
        print_with_color(last_act, "magenta")
        if "FINISH" in act:
            return ["FINISH"]
        act_name = act.split("(")[0]
        if act_name == "tap":
            params = re.findall(r"tap\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "long_press":
            params = re.findall(r"long_press\((.*?)\)", act)[0].split(",")
            area = int(params[0].strip())
            subarea = params[1].strip()[1:-1]
            return [act_name + "_grid", area, subarea, last_act]
        elif act_name == "swipe":
            params = re.findall(r"swipe\((.*?)\)", act)[0].split(",")
            start_area = int(params[0].strip())
            start_subarea = params[1].strip()[1:-1]
            end_area = int(params[2].strip())
            end_subarea = params[3].strip()[1:-1]
            return [act_name + "_grid", start_area, start_subarea, end_area, end_subarea, last_act]
        elif act_name == "grid":
            return [act_name]
        else:
            print_with_color(f"ERROR: Undefined act {act_name}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the model response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]


def parse_reflect_rsp(rsp):
    try:
        # decision = re.findall(r"Decision: (.*?)$", rsp, re.MULTILINE)[0]
        # think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0]
        decision = re.findall(r"Decision: (.*?)$", rsp, re.MULTILINE)[0].strip()
        think = re.findall(r"Thought: (.*?)$", rsp, re.MULTILINE)[0].strip() 
        #TODO:这里似乎会导致多余的空格
        print_with_color("Decision:", "yellow")
        print_with_color(decision, "magenta")
        print_with_color("Thought:", "yellow")
        print_with_color(think, "magenta")
        if decision == "INEFFECTIVE":
            return [decision, think]
        elif decision == "BACK" or decision == "CONTINUE" or decision == "SUCCESS":
            doc = re.findall(r"Documentation: (.*?)$", rsp, re.MULTILINE)[0]
            print_with_color("Documentation:", "yellow")
            print_with_color(doc, "magenta")
            return [decision, think, doc]
        else:
            print_with_color(f"ERROR: Undefined decision {decision}!", "red")
            return ["ERROR"]
    except Exception as e:
        print_with_color(f"ERROR: an exception occurs while parsing the model response: {e}", "red")
        print_with_color(rsp, "red")
        return ["ERROR"]
