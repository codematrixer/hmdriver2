

# 模块介绍
```
├── README.md
├── docs
│   ├── _hypium_api.md
│   └── DEVELOP.md
├── hmdriver2
│   ├── __init__.py
│   ├── _client.py      // 和鸿蒙uitest通信的客户端
│   ├── _gesture.py     // 复杂手势操作封装
│   ├── _uiobject.py    // ui控件对象, 提供操作控件和获取控件属性接口
│   ├── asset
│   │   └── agent.so   // 鸿蒙uitest动态链路库
│   ├── driver.py      // ui自动化核心功能类, 提供设备点击/滑动操作, app启动停止等常用功能
│   ├── exception.py
│   ├── hdc.py        // hdc命令封装
│   └── proto.py
│   └── utils.py
├── pyproject.toml
├── .flake8
└── tests         // 自测用例
    ├── __init__.py
    ├── test_client.py
    ├── test_driver.py
    └── test_element.py

```


# uitest协议

## By
### On.text

**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"On.text","this":"On#seed","args":["精选"],"message_type":"hypium"},"request_id":"20240829202019513472","client":"127.0.0.1"}
```
**recv**
```
{"result":"On#1"}
```

### On.id
###  On.key
###  On.type


### On.isAfter
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"On.isAfter","this":"On#seed","args":["On#3"],"message_type":"hypium"},"request_id":"20240830143213340263","client":"127.0.0.1"}
```
**recv**
```
{"result":"On#4"}
```

### On.isBefore
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"On.isBefore","this":"On#seed","args":["On#3"],"message_type":"hypium"},"request_id":"20240830143213340263","client":"127.0.0.1"}
```
**recv**
```
{"result":"On#4"}
```

## Driver
### create
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.create","this":null,"args":[],"message_type":"hypium"},"request_id":"20240830153517897539","client":"127.0.0.1"}
```
**recv**
```
{"result":["Component#0"]}
```

### getDisplaySize
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.getDisplaySize","this":"Driver#0","args":[],"message_type":"hypium"},"request_id":"20240830151015274374","client":"127.0.0.1"}
```
**recv**
```
{"result":{"x":1260,"y":2720}}
```

### getDisplayRotation
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.getDisplayRotation","this":"Driver#0","args":[],"message_type":"hypium"},"request_id":"20240830151015274374","client":"127.0.0.1"}
```
**recv**
```
{"result":0}
{"result":1}
{"result":2}
{"result":3}
```

### click
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.click","this":"Driver#0","args":[100,300],"message_type":"hypium"},"request_id":"20240830151533693140","client":"127.0.0.1"}
```
**recv**
```
{"result":null}
```

### doubleClick
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.doubleClick","this":"Driver#0","args":[630,1360],"message_type":"hypium"},"request_id":"20240830152159243541","client":"127.0.0.1"}
```
**recv**
```
{"result":null}
```

### longClick
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.longClick","this":"Driver#0","args":[630,1360],"message_type":"hypium"},"request_id":"20240830152159243541","client":"127.0.0.1"}
```
**recv**
```
{"result":null}
```

### swipe
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.swipe","this":"Driver#0","args":[630,2176,630,1360,7344],"message_type":"hypium"},"request_id":"20240913123029322117","client":"127.0.0.1"}
```
**recv**
```
{"result":null}
```


### findComponents
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.findComponents","this":"Driver#0","args":["On#1"],"message_type":"hypium"},"request_id":"20240830143210219186","client":"127.0.0.1"}
```
**recv**
```
{"result":["Component#7","Component#8"]}
```

### findComponent
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.findComponent","this":"Driver#0","args":["On#2"],"message_type":"hypium"},"request_id":"20240830143211753489","client":"127.0.0.1"}
```
**recv**
```
{"result":"Component#1"}

# {"result":null}
```

### waitForComponent
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.waitForComponent","this":"Driver#0","args":["On#0",10000],"message_type":"hypium"},"request_id":"20240829202019518844","client":"127.0.0.1"}
```
**recv**
```
{"result":"Component#0"}
```

### findWindow
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.findWindow","this":"Driver#0","args":[{"actived":true}],"message_type":"hypium"},"request_id":"20240829202019518844","client":"127.0.0.1"}
```
**recv**
```
{"result":"UiWindow#10"}
```

### uiEventObserverOnce
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.uiEventObserverOnce","this":"Driver#0","args":["toastShow"],"message_type":"hypium"},"request_id":"20240905144543056211","client":"127.0.0.1"}
```
**recv**
```
{"result":true}
```


### getRecentUiEvent
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.getRecentUiEvent","this":"Driver#0","args":[3000],"message_type":"hypium"},"request_id":"20240905143857794307","client":"127.0.0.1"}
```
**recv**
```
{"result":{"bundleName":"com.samples.test.uitest","text":"testMessage","type":"Toast"}}
```

### PointerMatrix.create
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"PointerMatrix.create","this":null,"args":[1,104],"message_type":"hypium"},"request_id":"20240906204116056319"}
```
**recv**
```
{"result":"PointerMatrix#0"}
```

### PointerMatrix.setPoint
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"PointerMatrix.setPoint","this":"PointerMatrix#0","args":[0,0,{"x":65536630,"y":984}],"message_type":"hypium"},"request_id":"20240906204116061416"}

{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"PointerMatrix.setPoint","this":"PointerMatrix#0","args":[0,1,{"x":3277430,"y":984}],"message_type":"hypium"},"request_id":"20240906204116069343"}

{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"PointerMatrix.setPoint","this":"PointerMatrix#0","args":[0,2,{"x":3277393,"y":994}],"message_type":"hypium"},"request_id":"20240906204116072723"}

...

{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"PointerMatrix.setPoint","this":"PointerMatrix#0","args":[0,102,{"x":2622070,"y":1632}],"message_type":"hypium"},"request_id":"20240906204116359992"}

{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"PointerMatrix.setPoint","this":"PointerMatrix#0","args":[0,103,{"x":633,"y":1632}],"message_type":"hypium"},"request_id":"20240906204116363228"}
```
**recv**
```
{"result":null}
```

### injectMultiPointerAction
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Driver.injectMultiPointerAction","this":"Driver#0","args":["PointerMatrix#0",2000],"message_type":"hypium"},"request_id":"20240906204116366578"}
```
**recv**
```
{"result":true}
```


## Component
### Component.getId
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.getId","this":"Component#1","args":[],"message_type":"hypium"},"request_id":"20240830143213283547","client":"127.0.0.1"}
```
**recv**
```
{"result":""}
```
### Component.getKey (getId)
### Component.getType
### Component.getText
### Component.getDescription
### Component.isSelected
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.isSelected","this":"Component#28","args":[],"message_type":"hypium"},"request_id":"20240830200628395802","client":"127.0.0.1"}
```
**recv**
```
{"result":false}
```
### Component.isChecked
### Component.isEnabled
### Component.isFocused
### Component.isCheckable
### Component.isClickable
### Component.isLongClickable
### Component.getBounds
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.getBounds","this":"Component#28","args":[],"message_type":"hypium"},"request_id":"20240830200628840692","client":"127.0.0.1"}
```
**recv**
```
{"result":{"bottom":1412,"left":832,"right":1125,"top":1282}}
```
### Component.getBoundsCenter
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.getBoundsCenter","this":"Component#28","args":[],"message_type":"hypium"},"request_id":"20240830200628840692","client":"127.0.0.1"}
```
**recv**
```
{"result":{"x":978,"y":1347}}
```

### Component.click
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.click","this":"Component#2","args":[],"message_type":"hypium"},"request_id":"20240903163157355953","client":"127.0.0.1"}
```
**recv**
```
 {"result":null}
```

### Component.doubleClick
### Component.longClick
### Component.dragTo
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.dragTo","this":"Component#2","args":["Component#3"],"message_type":"hypium"},"request_id":"20240903163204255727","client":"127.0.0.1"}
```
**recv**
```
 {"result":null}
```
### Component.inputText
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.inputText","this":"Component#1","args":["ccc"],"message_type":"hypium"},"request_id":"20240903162837676456","client":"127.0.0.1"}
```
**recv**
```
 {"result":null}
```
### Component.clearText
**send**
```
{"module":"com.ohos.devicetest.hypiumApiHelper","method":"callHypiumApi","params":{"api":"Component.clearText","this":"Component#1","args":[],"message_type":"hypium"},"request_id":"20240903162837676456","client":"127.0.0.1"}
```
**recv**
```
 {"result":null}
```
### Component.pinchIn
### Component.pinchOut


## HDC
https://github.com/codematrixer/awesome-hdc