/*
Copyright (C) 2025 AIDC-AI
This project is licensed under the MIT License (SPDX-License-identifier: MIT).
*/
function initMessage() {
    // 时间配置常量 - 可根据性能需要调整
    const TIMING_CONFIG = {
        PAGE_LOAD_DELAY: 150,        // 页面加载后等待时间 (ms) - 确保DOM稳定和React渲染完成
        BUTTON_CHECK_INTERVAL: 100,  // 按钮查找重试间隔 (ms) - starter按钮检测频率
        BASIC_ELEMENT_CHECK_INTERVAL: 200,  // 基础元素检查间隔 (ms) - 页面初始化检测频率
        MAX_RETRY_COUNT: 50,         // 最大重试次数 - 避免无限循环
    };

    // 获取URL参数
    function getUrlParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    // 检查并自动触发URL参数中的starter
    function checkAndTriggerUrlStarter() {
        const starterId = getUrlParam('starter');
        if (starterId) {
            // 处理URL编码和空格转换
            const decodedStarterId = decodeURIComponent(starterId);
            const normalizedStarterId = decodedStarterId.replace(/\s+/g, '-'); // 将空格替换为连字符
            const targetElementId = `starter-${normalizedStarterId}`;

            // 等待starter按钮准备好
            let retryCount = 0;
            const waitForStarterAndTrigger = () => {
                if (retryCount >= TIMING_CONFIG.MAX_RETRY_COUNT) {
                    return;
                }

                const starterButton = document.getElementById(targetElementId);
                if (starterButton) {
                    // 检查按钮是否真正可用
                    const isButtonReady = starterButton.offsetParent !== null && // 元素可见
                                         !starterButton.disabled &&              // 未禁用
                                         starterButton.style.display !== 'none'; // 未隐藏

                    if (isButtonReady) {
                        // 稍微延迟确保页面完全加载和React渲染完成
                        setTimeout(() => {
                            try {
                                // 再次确认按钮仍然存在且可用
                                const buttonCheck = document.getElementById(targetElementId);
                                if (buttonCheck && !buttonCheck.disabled) {
                                    buttonCheck.click();
                                }
                            } catch (error) {
                            }
                        }, TIMING_CONFIG.PAGE_LOAD_DELAY);
                    } else {
                        retryCount++;
                        setTimeout(waitForStarterAndTrigger, TIMING_CONFIG.BUTTON_CHECK_INTERVAL);
                    }
                } else {
                    // 如果starter按钮还没准备好，继续等待
                    retryCount++;
                    setTimeout(waitForStarterAndTrigger, TIMING_CONFIG.BUTTON_CHECK_INTERVAL);
                }
            };

            waitForStarterAndTrigger();
        }
    }

    // 初始化
    function init() {
        const checkReady = () => {
            // 等待页面基础元素和React应用加载完成
            const isPageReady = document.body && 
                               document.getElementById('starters') && // starter容器存在
                               document.querySelectorAll('[id^="starter-"]').length > 0; // 至少有一个starter按钮
            
            if (isPageReady) {
                // 检查URL参数并自动触发starter
                checkAndTriggerUrlStarter();
            } else {
                setTimeout(checkReady, TIMING_CONFIG.BASIC_ELEMENT_CHECK_INTERVAL);
            }
        };
        checkReady();
    }

    // 初始化
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
}

initMessage();
