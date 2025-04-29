# PERSONALAppAgent



## 🚀 Quick Start

This section will guide you on how to quickly use `gpt-4o-mini` as an agent to complete specific tasks for you on
your Android app.

### ⚙️ Step 1. Prerequisites

1. On your PC, download and install [Android Debug Bridge](https://developer.android.com/tools/adb) (adb) which is a
   command-line tool that lets you communicate with your Android device from the PC.

2. Get an Android device and enable the USB debugging that can be found in Developer Options in Settings.

3. Connect your device to your PC using a USB cable.

4. (Optional) If you do not have an Android device but still want to try PersonalAppAgent. We recommend you download
   [Android Studio](https://developer.android.com/studio/run/emulator) and use the emulator that comes with it.
   The emulator can be found in the device manager of Android Studio. You can install apps on an emulator by
   downloading APK files from the internet and dragging them to the emulator.
   PersonalAppAgent can detect the emulated device and operate apps on it just like operating a real device.

5. Clone this repo and install the dependencies. All scripts in this project are written in Python 3 so make sure you
   have installed it.

```bash
cd PERSONALAPPAGENT
pip install -r requirements.txt
```

### 🤖 Step 2. Configure the Agent

PersonalAppAgent needs to be powered by a multi-modal model which can receive both text and visual inputs. During our experiment
, we used `gpt-4o-mini` as the model to make decisions on how to take actions to complete a task on the smartphone.

To configure your requests to GPT-4o-mini, you should modify `config.yaml` in the root directory.
There are two key parameters that must be configured to try PersonalAppAgent:

1. OpenAI API key: you must purchase an eligible API key from OpenAI so that you can have access to GPT-4o-mini.
2. Request interval: this is the time interval in seconds between consecutive GPT-4o-mini requests to control the frequency 
   of your requests to GPT-4o-mini. Adjust this value according to the status of your account.

Other parameters in `config.yaml` are well commented. Modify them as you need.

If you want to test PersonalAppAgent using your own models, you should write a new model class in `scripts/model.py` accordingly.

### 🔍 Step 3. Exploration Phase

Our paper proposed a novel solution that involves two phases, exploration, and deployment, to turn GPT-4o-mini into a capable 
agent that can help users operate their Android phones when a task is given. The exploration phase starts with a task 
given by you, and you can choose to let the agent either explore the app on its own or learn from your demonstration. 
In both cases, the agent generates documentation for elements interacted during the exploration/demonstration and 
saves them for use in the deployment phase.

#### Option 1: Autonomous Exploration

This solution features a fully autonomous exploration which allows the agent to explore the use of the app by attempting
the given task without any intervention from humans.

To start, run `learn.py` in the root directory. Follow the prompted instructions to select `autonomous exploration` 
as the operating mode and provide the app name and task description. Then, your agent will do the job for you. Under 
this mode, PersonalAppAgent will reflect on its previous action making sure its action adheres to the given task and generate 
documentation for the elements explored.

```bash
python learn.py
```

#### Option 2: Learning from Human Demonstrations

This solution requires users to demonstrate a similar task first. PersonalAppAgent will learn from the demo and generate 
documentations for UI elements seen during the demo.

To start human demonstration, you should run `learn.py` in the root directory. Follow the prompted instructions to select 
`human demonstration` as the operating mode and provide the app name and task description. A screenshot of your phone 
will be captured and all interactive elements shown on the screen will be labeled with numeric tags. You need to follow 
the prompts to determine your next action and the target of the action. When you believe the demonstration is finished, 
type `stop` to end the demo.

```bash
python learn.py
```

![](./assets/demo.png)

### 📱 Step 4. Deployment Phase

After the exploration phase finishes, you can run `run.py` or `fronted.py`in the root directory. Follow the prompted instructions to enter 
the name of the app, select the appropriate documentation base you want the agent to use and provide the task 
description. Then, your agent will do the job for you. The agent will automatically detect if there is documentation 
base generated before for the app; if there is no documentation found, you can also choose to run the agent without any 
documentation (success rate not guaranteed).

```bash
streamlit run fronted.py
```




