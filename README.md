# hmdriver2
hmdriver2是一款支持鸿蒙Next系统的UI自动化框架，提供应用管理（启动/停止/获取应用列表等），UI操作（（点击/滑动/输入/元素查找等））等功能，实现鸿蒙应用的自动化测试。

# why hmdirver2
在写这个项目前github上已有个[hmdirver](https://github.com/mrx1203/hmdriver)框架，但它是侵入式的，需要提前在手机端安装一个app，通过这个app将鸿蒙系统@ohos.UiTest的基础能力暴露出来，最终实现python调用。

鸿蒙官方也提供了一个自动化框架叫hypium，但是我认为它的使用很复杂，依赖也很多，不够友好。

于是结合hypium和hmdriver的优势，决定重写一套框架hmdirver2


# Advantage
- 支持鸿蒙Next系统的任何设备
- 无侵入式，无需在手机安装基于arkTS的UiTest APP
- 稳定高效，client端直接和鸿蒙底层uitest socket服务通信
- 使用python语言编写测试用例，上手简单，即插即用

# Install
```
pip3 install hmdirver2
```

# Usage



# Refer to

- https://developer.huawei.com/consumer/cn/doc/harmonyos-guides-V5/ut-V5
- https://github.com/mrx1203/hmdriver