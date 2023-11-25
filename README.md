# GenshinMummy

## 简介

原神妈妈是一个基于计算机视觉和RPA的脚本工具。

## 项目安装

``` shell
# 进入项目目录
cd GenshinMummy

pip install .
```

## 解锁垃圾圣遗物
1. 使用管理员权限打开终端，然后执行加解锁圣遗物脚本
```shell
python .\genshin_mummy\artifact_helper\unlock_shit_artifact.py
```
2. 自己加解锁一个圣遗物，如果加锁后有提示页，记得选不再提示，然后把加提示关闭。
3. 你有10s的时间，切换到圣遗物页面，并选中最左上角圣遗物。
4. 脱手，玩手机去吧，等它慢慢加解锁吧。【别和它抢鼠标~】

## 圣遗物加解锁逻辑
目前加解锁逻辑是这样的，比较保守，不过也够拎出来狗粮了。

1. 等级大于0=>锁
2. 非五星=>不锁
3. 沙、杯、帽主词条为类别独有词条=>锁
4. 双暴词条=>锁
5. 初始四词条 且不要存在所有小攻防命都有=>锁
6. 小攻击、小防御、小生命大于等于两个=>不锁
7. 其余情况保险起见=>锁


## 待办

23333，毕竟是自用脚本，纯引擎，所以零用户体验。

大概就是每次圣遗物爆仓+自己还有时间，可能会回来优化一些内容。


## GPU版本
PaddleOCR对高版本的CUDA不兼容，个人日用电脑CUDA来切去太烦了，默认用CPU版本。
```shell
# 卸载CPU版本的PADDLE
pip unintall paddlepaddle
# 安装GPU版本的PADDLE
pip install paddlepaddle-gpu
```
GPU版本依赖：CUDA10.1 / CUDA10.2 + CUDNN 7.6

参考官方文档：
https://github.com/PaddlePaddle/PaddleOCR/blob/release/2.7/doc/doc_ch/environment.md

