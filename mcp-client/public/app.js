/*
Copyright (C) 2025 AIDC-AI
This project is licensed under the MIT License (SPDX-License-identifier: MIT).
*/
function initMessage() {
    // console.log("Message module initialized");

    // 时间配置常量 - 可根据性能需要调整
    const TIMING_CONFIG = {
        PAGE_LOAD_DELAY: 150,        // 页面加载后等待时间 (ms) - 确保DOM稳定和React渲染完成
        BUTTON_CHECK_INTERVAL: 100,  // 按钮查找重试间隔 (ms) - starter按钮检测频率
        BASIC_ELEMENT_CHECK_INTERVAL: 200,  // 基础元素检查间隔 (ms) - 页面初始化检测频率
        MAX_RETRY_COUNT: 50,         // 最大重试次数 - 避免无限循环
        URL_CLEAR_DELAY: 1000        // 清除URL参数的延迟时间 (ms) - 确保操作完成
    };

    // 获取URL参数
    function getUrlParam(param) {
        const urlParams = new URLSearchParams(window.location.search);
        return urlParams.get(param);
    }

    // 诊断页面状态 - 用于调试
    function diagnosePage() {
        const starterButtons = document.querySelectorAll('[id^="starter-"]');
        console.log('=== 页面状态诊断 ===');
        console.log('当前URL:', window.location.href);
        console.log('document.readyState:', document.readyState);
        console.log('starters容器:', document.getElementById('starters'));
        console.log('starter按钮总数:', starterButtons.length);
        
        starterButtons.forEach((btn, index) => {
            console.log(`按钮${index + 1}:`, {
                id: btn.id,
                visible: btn.offsetParent !== null,
                disabled: btn.disabled,
                display: btn.style.display,
                classList: Array.from(btn.classList)
            });
        });
        console.log('=== 诊断结束 ===');
    }

    // 检查并自动触发URL参数中的starter
    function checkAndTriggerUrlStarter() {
        const starterId = getUrlParam('starter');
        if (starterId) {
            console.log('检测到URL参数starter ID:', starterId);

            // 处理URL编码和空格转换
            const decodedStarterId = decodeURIComponent(starterId);
            const normalizedStarterId = decodedStarterId.replace(/\s+/g, '-'); // 将空格替换为连字符
            const targetElementId = `starter-${normalizedStarterId}`;

            console.log('URL参数:', starterId);
            console.log('解码后:', decodedStarterId);
            console.log('标准化后:', normalizedStarterId);
            console.log('目标元素ID:', targetElementId);

            // 等待starter按钮准备好
            let retryCount = 0;
            const waitForStarterAndTrigger = () => {
                if (retryCount >= TIMING_CONFIG.MAX_RETRY_COUNT) {
                    console.error('达到最大重试次数，停止尝试:', targetElementId);
                    diagnosePage(); // 诊断失败时的页面状态
                    return;
                }

                const starterButton = document.getElementById(targetElementId);
                if (starterButton) {
                    // 检查按钮是否真正可用
                    const isButtonReady = starterButton.offsetParent !== null && // 元素可见
                                         !starterButton.disabled &&              // 未禁用
                                         starterButton.style.display !== 'none'; // 未隐藏

                    if (isButtonReady) {
                        console.log('找到starter按钮且已就绪，准备触发:', targetElementId);
                        console.log('按钮状态检查 - 可见:', starterButton.offsetParent !== null, 
                                   '启用:', !starterButton.disabled, 
                                   '显示:', starterButton.style.display !== 'none');
                        
                        // 稍微延迟确保页面完全加载和React渲染完成
                        setTimeout(() => {
                            try {
                                // 再次确认按钮仍然存在且可用
                                const buttonCheck = document.getElementById(targetElementId);
                                if (buttonCheck && !buttonCheck.disabled) {
                                    console.log('最终确认按钮可用，执行点击:', targetElementId);
                                    buttonCheck.click();
                                    console.log('已触发starter按钮:', buttonCheck.id);
                                    
                                    // 延迟清除URL参数，确保点击操作完全完成
                                    setTimeout(() => {
                                        const newUrl = window.location.origin + window.location.pathname;
                                        window.history.replaceState({}, document.title, newUrl);
                                        console.log('已清除URL参数');
                                    }, TIMING_CONFIG.URL_CLEAR_DELAY);
                                } else {
                                    console.warn('最终检查时按钮不可用:', targetElementId);
                                    diagnosePage(); // 诊断最终检查失败时的状态
                                }
                            } catch (error) {
                                console.error('点击按钮时出错:', error);
                            }
                        }, TIMING_CONFIG.PAGE_LOAD_DELAY);
                    } else {
                        console.log('按钮存在但未就绪，继续等待:', targetElementId, 
                                   '可见:', starterButton.offsetParent !== null, 
                                   '启用:', !starterButton.disabled);
                        retryCount++;
                        setTimeout(waitForStarterAndTrigger, TIMING_CONFIG.BUTTON_CHECK_INTERVAL);
                    }
                } else {
                    // 如果starter按钮还没准备好，继续等待
                    retryCount++;
                    console.log(`starter按钮尚未找到，继续等待 (${retryCount}/${TIMING_CONFIG.MAX_RETRY_COUNT}):`, targetElementId);
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
                console.log('页面和React应用已就绪，开始检查starter参数');
                // 诊断页面状态
                diagnosePage();
                // 检查URL参数并自动触发starter
                checkAndTriggerUrlStarter();
            } else {
                console.log('等待页面就绪 - body:', !!document.body, 
                           'starters容器:', !!document.getElementById('starters'),
                           'starter按钮数量:', document.querySelectorAll('[id^="starter-"]').length);
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
