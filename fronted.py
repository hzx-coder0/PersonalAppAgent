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
        page_title="PersonalAppAgent",
        layout="centered", 
    )
    st.markdown(
        """
        <style>
        #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4{
            max-width:900px; /* 设置最大宽度 */
            margin-top:-80px;
            margin-bottom:auto; /* 上下外边距为0，左右自动 */
            margin-right:auto;
            margin-left:auto;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    st.markdown('<div class="title"><h1>PersonalAppAgent</h1></div>', unsafe_allow_html=True)  # 显示标题
    with st.container():
        col1, col2, col3, col4 = st.columns([2,3,6,2], gap="medium")  # 创建三列
        # st.markdown('''
        # <style>
        #     #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-434r0z.eu6p4el0 > div.stColumn.st-emotion-cache-zosxzd.eu6p4el2 > div{
        #         position: absolute;
        #         left: 360px;}
        #     #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-434r0z.eu6p4el0 > div:nth-child(2) > div{
        #         position: absolute;
        #         left: 170px;}
        # </style>''', 
        # unsafe_allow_html=True)
        with col1:
            devices = list_all_devices() or ["No device connected"]  # 如果没有设备，显示默认选项
            device_name = st.selectbox("Device Name:", devices, key="device_name")  # 使用单选框选择设备
            controller = AndroidController(device_name) # 创建 AndroidController 实例
                
        with col2:
            # 获取 apps 文件夹下的子文件夹名称
            apps_dir = "./apps"  # 假设 apps 文件夹在当前目录下
            if os.path.exists(apps_dir) and os.path.isdir(apps_dir):
                app_folders = [folder for folder in os.listdir(apps_dir) if os.path.isdir(os.path.join(apps_dir, folder))]
            else:
                app_folders = ["No apps available"]  # 如果文件夹不存在或为空

            # 创建单选框
            app_name = st.selectbox("Select App Name:", app_folders, key="app_name")  # 使用单选框选择 App 名称
        with col3:
            # 展示思考过程
            # app_name = st.text_input("App Name:", "", key="app_name")  # 输入 App 名称
            # instruction = st.text_area("Enter your instruction：", "", key="instruction")  # 输入指令
            instruction = st.text_input("Enter your instruction：", "", key="instruction")  # 输入指令
        with col4:
            st.markdown(
                """
                <style>
                #root > div:nth-child(1) > div.withScreencast > div > div > section > div.stMainBlockContainer.block-container.st-emotion-cache-mtjnbi.eht7o1d4 > div > div > div > div.st-emotion-cache-0.eu6p4el5 > div > div > div.stHorizontalBlock.st-emotion-cache-434r0z.eu6p4el0 > div:nth-child(4) > div > div > div > div:nth-child(2){
                    position: absolute;
                    top: 28px;
                }
                </style>
                """,
                unsafe_allow_html=True,
            )
            execute_button = st.button("Run")  # 执行按钮
        with st.container(height=900, border=False):
            main_container = st.empty()  # 创建一个空的容器，用于存放输出内容
            main_contain = []
            # 初始化历史记录列表
            observation_history = []
            thinking_history = []
            action_history = []
            summary_history = []
            st.markdown(
                """
                <style>
                .main-container {
                    max-width: 900px; /* 设置最大宽度 */
                    margin: 0 auto; /* 上下外边距为0，左右自动 */
                    padding: 20px; /* 内边距 */
                }
                .instrcution-container {
                    padding: 10px; /* 内边距 */
                    margin-bottom: 5px; /* 区域之间的间距 */
                    margin-top: -15px; /* 区域之间的间距 */
                    margin-left: -20px; /* 区域之间的间距 */
                    font-size: 18px; /* 设置字体大小 */
                }
                .observation-container {
                    padding: 10px; /* 内边距 */
                    margin-bottom: 5px; /* 区域之间的间距 */
                    margin-top: -15px; /* 区域之间的间距 */
                    margin-left: -20px; /* 区域之间的间距 */
                }
                .thinking-container {
                    padding: 10px; /* 内边距 */
                    margin-top: 10px; /* 区域之间的间距 */
                    margin-bottom: 5px; /* 区域之间的间距 */
                    margin-left: -20px; /* 区域之间的间距 */
                }
                .action-container {
                    padding: 10px; /* 内边距 */
                    margin-top: 10px; /* 区域之间的间距 */
                    margin-bottom: 5px; /* 区域之间的间距 */
                    margin-left: -20px; /* 区域之间的间距 */
                }
                .summary-container {
                    padding: 10px; /* 内边距 */
                    margin-top: 10px; /* 区域之间的间距 */
                    margin-bottom: 5px; /* 区域之间的间距 */
                    margin-left: -20px; /* 区域之间的间距 */
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
            html_content = "<div class='main-container'></div>"
            # 测试长文本是否能正常显示
            # html_content = "<div class='main-container'></div>"
            # html_content = html_content[:html_content.rfind("</div>")] # 截取到最后一个 </div> 标签
            # for i in range(1, 1200):
            #     html_content = f"{html_content}<h3>⭐ step {i}</h3>"
            # html_content += "</div>"
            main_container.markdown(html_content, unsafe_allow_html=True)
    if execute_button:
        with st.spinner("thinking..."):
            # 处理按钮点击事件
            # 当输出还未完成时，显示加载动画
            html_content = "<div class='main-container'></div>"
            # 处理输入的指令
            step = 1
            observation = ""
            thinking = ""
            action = ""
            summary = ""
            observation_flag = False
            thinking_flag = False
            action_flag = False
            summary_flag = False
            if instruction:
                print(f"Processing instruction: {instruction}")
                html_content = html_content[:html_content.rfind("</div>")] # 截取到最后一个 </div> 标签
                html_content += f"<div class='instrcution-container'><strong>💡 Instruction</strong>: {instruction}</br></div>"
                html_content += f"<h4>⭐ step {step}</h4></div>"
                main_container.markdown(html_content, unsafe_allow_html=True)
                try:
                    async for rsp, chunk in task_executor_async(device_name, app_name, instruction):
                        
                        if rsp:
                            # 处理响应
                            # 转换为字符串
                            rsp = str(rsp)
                            chunk = str(chunk)
                            # 当有Observation时，而没有Thought、Action和Summary时
                            main_container.markdown(html_content, unsafe_allow_html=True)
                            if "Observation:" in rsp and "Thought" not in rsp and "Action" not in rsp and "Summary" not in rsp:
                                if not observation_flag:
                                    observation_flag = True
                                    html_content = html_content[:html_content.rfind("</div>")] # 截取到最后一个 </div> 标签
                                    html_content += f"<div class='observation-container'><strong>👀 Observation</strong>:</br></div></div>"
                                    # 第一个chunk是冒号，跳过
                                    continue
                                observation += chunk
                                observation = re.sub(r'^[:\s]*[:\s]*', '', observation)
                                observation = re.sub(r'\s+', ' ', observation)
                                html_content = html_content[:html_content.rfind("</div>")] # 截取到最后一个 </div> 标签
                                html_content = html_content[:html_content.rfind("</div>")] # 截取到最后一个 </div> 标签
                                html_content += chunk + "</div></div>"
                                main_container.markdown(html_content, unsafe_allow_html=True)


                            # 更新 thinking
                            if "Thought:" in rsp and "Action" not in rsp and "Summary" not in rsp:
                                if not thinking_flag:
                                    thinking_flag = True
                                    html_content = html_content[:html_content.rfind("</div>")]
                                    html_content += f"<div class='thinking-container'><strong>💭 Thinking</strong>:</br></div></div>"
                                    continue
                                thinking += chunk
                                thinking = re.sub(r'^[:\s]*[:\s]*', '', thinking)
                                thinking = re.sub(r'\s+', ' ', thinking)
                                html_content = html_content[:html_content.rfind("</div>")]
                                html_content = html_content[:html_content.rfind("</div>")]
                                html_content += chunk + "</div></div>"
                                main_container.markdown(html_content, unsafe_allow_html=True)


                            # 更新 action
                            if "Action:" in rsp and "Summary" not in rsp:
                                if not action_flag:
                                    action_flag = True
                                    html_content = html_content[:html_content.rfind("</div>")]
                                    html_content += f"<div class='action-container'><strong>⚡ Action</strong>:</br></div></div>"
                                    continue
                                action += chunk
                                action = re.sub(r'^[:\s]*[:\s]*', '', action)
                                action = re.sub(r'\s+', ' ', action)
                                html_content = html_content[:html_content.rfind("</div>")]
                                html_content = html_content[:html_content.rfind("</div>")]
                                html_content += chunk + "</div></div>"
                                main_container.markdown(html_content, unsafe_allow_html=True)

                            # 更新 summary
                            if "Summary:" in rsp:
                                if not summary_flag:
                                    summary_flag = True
                                    html_content = html_content[:html_content.rfind("</div>")]
                                    html_content += f"<div class='summary-container'><strong>📝 Summary</strong>:</br></div></div>"
                                    continue
                                summary += chunk
                                summary = re.sub(r'^[:\s]*[:\s]*', '', summary)
                                summary = re.sub(r'\s+', ' ', summary)
                                html_content = html_content[:html_content.rfind("</div>")]
                                html_content = html_content[:html_content.rfind("</div>")]
                                html_content += chunk + "</div></div>"
                                main_container.markdown(html_content, unsafe_allow_html=True)
                        if chunk == "the action has been executed":
                            observation_history.append(observation)
                            thinking_history.append(thinking)
                            action_history.append(action)
                            summary_history.append(summary)
                            main_contain.append(html_content)
                            observation = ""
                            thinking = ""
                            action = ""
                            summary = ""
                            observation_flag = False
                            thinking_flag = False
                            action_flag = False
                            summary_flag = False
                            step += 1
                            html_content = html_content[:html_content.rfind("</div>")] # 截取到最后一个 </div> 标签
                            html_content += "<hr style=\"border: 1px dashed #ccc; margin: 20px 0;\"> "# 添加虚分割线
                            html_content += f"</br><h4>⭐ step {step}</h4></div>"
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.exception(e)
        

if __name__ == "__main__":
    asyncio.run(app())