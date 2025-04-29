import os
import streamlit as st
import asyncio
import time
import json_repair
import re
import sys
import json
from PIL import Image
from markdown import Markdown
from io import StringIO
# 把appagent/scripts目录添加到sys.path中
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'scripts')))
from scripts.and_controller import list_all_devices, AndroidController
from scripts.task_executor_async import task_executor_async


async def wait_screenshot(controller:AndroidController):
    screenshot = controller.get_screenshot(prefix="screenshot", save_dir="./tmp")
    return screenshot

async def trans_rsp(rsp):
    # 将rsp转换成html适合展示
    # 使用 Markdown 对象并禁用段落解析
    md = Markdown(output_format="html5")
    md.stripTopLevelTags = False  # 禁用顶级标签（如 <p>）
    html = StringIO()
    md.convert(rsp, html)
    return html.getvalue()

async def app():
    st.set_page_config(
        page_title="AppAgent",
        layout="centered", 
    )
    st.markdown(
        """
        <style>
        #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4{
            max-width: 1200px; /* 设置最大宽度 */
            margin-top:-80px;
            margin-bottom:auto; /* 上下外边距为0，左右自动 */
            margin-right:auto;
            margin-left:auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="title"><h1>AppAgent</h1></div>', unsafe_allow_html=True)  # 显示标题
    with st.container():
        ## TODO: 父级元素有问题
        st.markdown(
            """
            <style>
            #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-ocqkz7.eu6p4el0 > div:nth-child(2) > div > div > div > div > div > div > div > div > div > div.stImage.st-emotion-cache-1dvmtd8.evl31sl0 > div > img{
                position: relative;
                left: 50%;
                transform: translateX(-50%);
                }
            #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-ocqkz7.eu6p4el0 > div:nth-child(2){
                width: 323.02px;
            }
            #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-ocqkz7.eu6p4el0 > div.stColumn.st-emotion-cache-izb7bh.eu6p4el2{
                height: 708px;
            }
            #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-ocqkz7.eu6p4el0 > div:nth-child(1){
                height: 708px;
            }
            #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-ocqkz7.eu6p4el0 > div:nth-child(2){
                height: 708px;
            }
            </style>
            """,
            unsafe_allow_html=True,
        )
        col1, col2, col3 = st.columns([2,2,3], border=True)  # 创建三列
        with col1:
            with st.container():
                devices = list_all_devices() or ["No device connected"]  # 如果没有设备，显示默认选项
                device_name = st.selectbox("Device Name:", devices, key="device_name")  # 使用单选框选择设备
                controller = AndroidController(device_name) # 创建 AndroidController 实例
                # 获取 apps 文件夹下的子文件夹名称
                apps_dir = "./apps"  # 假设 apps 文件夹在当前目录下
                if os.path.exists(apps_dir) and os.path.isdir(apps_dir):
                    app_folders = [folder for folder in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, folder))]
                else:
                    app_folders = ["No apps available"]  # 如果文件夹不存在或为空

                # 创建单选框
                app_name = st.selectbox("Select App Name:", app_folders, key="app_name")  # 使用单选框选择 App 名称
                # app_name = st.text_input("App Name:", "", key="app_name")  # 输入 App 名称
                instruction = st.text_area("Enter your instruction：", "", key="instruction", height=200)  # 输入指令
                execute_button = st.button("Execute")  # 执行按钮
        with col2:
            # 展示手机截图
            with st.container():
                screenshot = st.empty()
                screenshot_path =await wait_screenshot(controller)
                try:
                    # 使用 Pillow 打开图片并调整大小
                    img = Image.open(screenshot_path)
                    max_width = 1000  # 设置最大宽度
                    max_height = 800  # 设置最大高度
                    img.thumbnail((max_width, max_height))  # 等比缩放图片
                    screenshot.image(img, caption="Device Screenshot", use_container_width=False)
                except Exception as e:
                    st.error(f"Failed to process image: {e}")
        with col3:
            # 展示思考过程
            with st.container():
                observation_process = st.empty()
                thinking_process = st.empty()
                action_process = st.empty()
                summary_process = st.empty()
                st.markdown('''
                    <style>
                        #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div > div.stColumn.st-emotion-cache-izb7bh.eu6p4el2 > div > div > div > div > div > div{
                                gap: 0rem;
                        }
                        #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-ocqkz7.eu6p4el0 > div.stColumn.st-emotion-cache-izb7bh.eu6p4el2 > div{
                            height: 100%;
                            display: flex;
                        }
                    </style>''', 
                unsafe_allow_html=True)
                # 添加自定义 CSS 样式，设置固定高度
                st.markdown(
                    """
                    <style>
                    .observation-container {
                        height: 190px; /* 设置每个区域的固定高度 */
                        overflow-y: auto; /* 如果内容超出高度，显示滚动条 */
                        padding: 10px; /* 内边距 */
                        margin-bottom: 5px; /* 区域之间的间距 */
                        margin-top: -15px; /* 区域之间的间距 */
                        margin-left: -20px; /* 区域之间的间距 */
                    }
                    .thinking-container {
                        height: 190px; /* 设置每个区域的固定高度 */
                        overflow-y: auto; /* 如果内容超出高度，显示滚动条 */
                        padding: 10px; /* 内边距 */
                        margin-top: 10px; /* 区域之间的间距 */
                        margin-bottom: 5px; /* 区域之间的间距 */
                        margin-left: -20px; /* 区域之间的间距 */
                    }
                    .action-container {
                        height: 150px; /* 设置每个区域的固定高度 */
                        overflow-y: auto; /* 如果内容超出高度，显示滚动条 */
                        padding: 10px; /* 内边距 */
                        margin-top: 10px; /* 区域之间的间距 */
                        margin-bottom: 5px; /* 区域之间的间距 */
                        margin-left: -20px; /* 区域之间的间距 */
                    }
                    .summary-container {
                        height: 150px; /* 设置每个区域的固定高度 */
                        overflow-y: auto; /* 如果内容超出高度，显示滚动条 */
                        padding: 10px; /* 内边距 */
                        margin-top: 10px; /* 区域之间的间距 */
                        margin-bottom: 5px; /* 区域之间的间距 */
                        margin-left: -20px; /* 区域之间的间距 */
                    }
                    .thinking-container::after,
                    .action-container::after,
                    .observation-container::after {
                        content: ""; /* 必须设置内容为空 */
                        position: absolute;
                        bottom: 0; /* 定位到容器底部 */
                        left: 0; /* 从容器左侧开始 */
                        width: 100%; /* 下划线宽度与容器一致 */
                        height: 1px; /* 下划线高度 */
                        border-bottom: 1px dashed #ccc; /* 添加下划虚线 */
                    }
                    .observation-container strong,
                    .thinking-container strong,
                    .action-container strong,
                    .summary-container strong {
                        font-size: 16px; /* 设置字体大小 */ 
                    }
                    #self-text {
                        font-size: 13px ;
                    }
                    </style>
                    """,
                    unsafe_allow_html=True,
                )
                # observation = "The current screen shows the weather app displaying the weather forecast for the next few days. I can see the temperatures and weather conditions for different times of the day as well as details for yesterday, today, and the upcoming days including Wednesday. The user wants to check the weather for Wednesday, which is represented by a UI element labeled with '14' that shows the forecast details."  
                # thinking = "To proceed with checking the details for Wednesday, I need to tap on the UI element labeled '14,' which will provide the detailed weather information. This task aligns with the user's desire to plan for activities within the community, such as arranging flowers for events, considering the weather conditions."  
                # action = "tap(14)"
                # summary = "I am currently accessing the Weather app to check detailed weather information for Wednesday, following my previous action of opening the app."
                observation = ""  # 初始化 observation
                thinking = ""
                action = ""  # 初始化 action
                summary = ""  # 初始化 summary
                # 在每个区域中应用固定高度的样式
                observation_process.markdown(f'<div class="observation-container"><strong>👀 Observation:</strong> <div id="self-text">{observation}</div></div>', unsafe_allow_html=True)
                thinking_process.markdown(f'<div class="thinking-container"><strong>💭 Thought:</strong> <div id="self-text">{thinking}</div></div>', unsafe_allow_html=True)
                action_process.markdown(f'<div class="action-container"><strong>⚡ Action:</strong> <strong style="font-size: 16px">{action}</strong></div>', unsafe_allow_html=True)
                summary_process.markdown(f'<div class="summary-container"><strong>📝 Summary:</strong> <div id="self-text">{summary}</div></div>', unsafe_allow_html=True)
                
                # thinking_process.markdown("Thinking process will be displayed here.")
    if execute_button:
        if instruction:
            print(f"Processing instruction: {instruction}") 
            try:
                async for rsp, chunk in task_executor_async(device_name, app_name, instruction):
                    
                    if rsp:
                        # 处理响应
                        # 转换为字符串
                        rsp = str(rsp)
                        chunk = str(chunk)
                        # 当有Observation时，而没有Thought、Action和Summary时
                        if "Observation:" in rsp and "Thought" not in rsp and "Action" not in rsp and "Summary" not in rsp:
                            observation += chunk
                            # 去掉多余的冒号和空格
                            observation = re.sub(r'^[:\s]*[:\s]*', '', observation)
                            # 将多余的空格替换为一个空格
                            observation = re.sub(r'\s+', ' ', observation)
                            observation_process.markdown(f'<div class="observation-container"><strong>👀 Observation:</strong> <div id="self-text">{observation}</div></div>', unsafe_allow_html=True)

                        if "Thought:" in rsp and "Action" not in rsp and "Summary" not in rsp:
                            thinking += chunk
                            # 去掉多余的冒号和空格
                            thinking = re.sub(r'^[:\s]*[:\s]*', '', thinking)
                            # 将多余的空格替换为一个空格
                            thinking = re.sub(r'\s+', ' ', thinking)
                            thinking_process.markdown(f'<div class="thinking-container"><strong>💭 Thought:</strong> <div id="self-text">{thinking}</div></div>', unsafe_allow_html=True)

                        if "Action:" in rsp and "Summary" not in rsp:
                            action += chunk
                            # 去掉多余的冒号和空格
                            action = re.sub(r'^[:\s]*[:\s]*', '', action)
                            # 将多余的空格替换为一个空格
                            action = re.sub(r'\s+', ' ', action)
                            action_process.markdown(f'<div class="action-container"><strong>⚡ Action:</strong> <strong style="font-size: 16px">{action}</strong></div>', unsafe_allow_html=True)

                        if "Summary:" in rsp:
                            summary += chunk
                            # 去掉多余的冒号和空格
                            summary = re.sub(r'^[:\s]*[:\s]*', '', summary)
                            # 将多余的空格替换为一个空格
                            summary = re.sub(r'\s+', ' ', summary)
                            summary_process.markdown(f'<div class="summary-container"><strong>📝 Summary:</strong> <div id="self-text">{summary}</div></div>', unsafe_allow_html=True)
                    if chunk == "the action has been executed":
                        time.sleep(3)
                        screenshot_path =await wait_screenshot(controller)
                        observation = ""  
                        thinking = ""  
                        action = ""
                        summary = ""
                        try:
                            # 使用 Pillow 打开图片并调整大小
                            img = Image.open(screenshot_path)
                            max_width = 1000  # 设置最大宽度
                            max_height = 800  # 设置最大高度
                            img.thumbnail((max_width, max_height))  # 等比缩放图片
                            screenshot.image(img, caption="Device Screenshot", use_container_width=False)
                        except Exception as e:
                            st.error(f"Failed to process image: {e}")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.exception(e)
        

if __name__ == "__main__":
    asyncio.run(app())