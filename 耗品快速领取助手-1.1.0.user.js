// ==UserScript==
// @name         耗品快速领取助手
// @namespace    ICT-GP
// @version      1.1.0
// @description  FLEX耗品快速检索，支持多料号批量输入，悬浮窗可自由拖动并自动吸附网页左右侧
// @author       ICT-郭平
// @match        http://10.57.9.64:9090/*
// @grant        GM_setClipboard
// @run-at       document-idle
// ==/UserScript==

(function () {
    'use strict';

    // ============================================================
    // FLEX 耗品资料
    // 后续增加耗品时，只需要按照下面格式继续添加即可：
    //
    // {
    //     name: "耗品名称",
    //     part: "料号",
    //     station: "工站",
    //     source: "FLEX"
    // }
    //
    // ============================================================

    const CONSUMABLES = [
        {
            name: "真空吸盘|SMC|ZP3-02UGS",
            part: "1950120030036A",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "笔头|Secote|F190站|K094587B03V0",
            part: "1950110050K12A",
            station: "F190",
            source: "FLEX"
        },
        {
            name: "喷嘴|TETE|F200站0.76喷嘴|3.02.27.00015",
            part: "1950130090504A",
            station: "F200",
            source: "FLEX"
        },
        {
            name: "喷嘴|TETE|F200站0.76喷嘴|3.02.27.00015",
            part: "1950080010126A",
            station: "F200",
            source: "FLEX"
        },
        {
            name: "压头|F160（190",
            part: "1950130260602A-01",
            station: "F160/F190",
            source: "FLEX"
        },
        {
            name: "压头|F160（190",
            part: "1950110050X3UA",
            station: "F160/F190",
            source: "FLEX"
        },
        {
            name: "压头|F160（190",
            part: "1950130260602A-02",
            station: "F160/F190",
            source: "FLEX"
        },
        {
            name: "平皮带||周长2860mm宽10mm厚1.5mm绿",
            part: "19501200101KDA",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "平皮带||周长1025mm宽10m厚1.5mm绿",
            part: "19501200101KFA",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "平皮带|国产|聚氨酯皮带|长2920宽9厚1.5|mm",
            part: "1950120014545A",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "S3压头",
            part: "1950110050JY0A",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "RF020 压块L 8200957718",
            part: "1950110050XYGA",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "传感器|西克|GTB2S-N1331|光电",
            part: "1950100011546A",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "洗手粉|黑手|3KG/箱",
            part: "1950010060104A",
            station: "",
            source: "FLEX"
        },
        {
            name: "适配器|国产|点胶针筒，30CC|绿色",
            part: "1950040010095A",
            station: "",
            source: "FLEX"
        },
        {
            name: "退锡水|联信|C220B站|透明|50ML",
            part: "1950090020516A",
            station: "",
            source: "FLEX"
        },
        {
            name: "丁腈手套|,M码|丁腈|蓝色|50双/盒",
            part: "1950030010405A",
            station: "",
            source: "FLEX"
        },
        {
            name: "平皮带|Quick|2154",
            part: "19501200102YNA",
            station: "F220",
            source: "FLEX"
        },
        {
            name: "传感器|明治|ST-303NA-W|槽型，",
            part: "1950120022520A",
            station: "F195极限感应器",
            source: "FLEX"
        },
        {
            name: "同步带S5M-150-1160|橡胶",
            part: "1950130090238A",
            station: "F200",
            source: "FLEX"
        },
        {
            name: "防静电平皮带 EMH35-2135-W10",
            part: "1950130020087A",
            station: "F195",
            source: "FLEX"
        },
        {
            name: "吸盘|国产|M-P4JN|",
            part: "1950130053844A",
            station: "F030",
            source: "FLEX"
        },
        {
            name: "缓冲器|国产|ACA1007-2|标准型",
            part: "1950110050866A-02",
            station: "上料机限位",
            source: "FLEX"
        },
        {
            name: "缓冲器|国产|ACA0806-2\n-3",
            part: "1950110050680A",
            station: "保压机",
            source: "FLEX"
        },
        {
            name: "缓冲器|国产|ACA0806-2\n-3",
            part: "1950110051741A",
            station: "保压机",
            source: "FLEX"
        },
        {
            name: "气缸|费斯托|DGST-6-40-PA|滑台",
            part: "1950120031844A",
            station: "F030",
            source: "FLEX"
        },
        {
            name: "折弯针|E230920-01271-026",
            part: "1950130053103A",
            station: "F030",
            source: "FLEX"
        },
        {
            name: "电磁阀|LEAD|4V130C06B双",
            part: "1950120031881A",
            station: "F030",
            source: "FLEX"
        },
        {
            name: "气缸|SMC|CDUJB6-15DM|折弯",
            part: "1950120033148A",
            station: "F030",
            source: "FLEX"
        },
        {
            name: "夹爪|Justech|载具夹爪4|E221874-01281-030-X1",
            part: "1950130052919A",
            station: "RF030",
            source: "FLEX"
        },
        {
            name: "包胶L型吸嘴|SECOTE|8201056739",
            part: "1950110050CBTA",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "吸盘|国产|PJG-8|真",
            part: "1950120034349A",
            station: "F150",
            source: "FLEX"
        },
        {
            name: "磁性开关-黑",
            part: "1950130051644A",
            station: "F030",
            source: "FLEX"
        },
        {
            name: "L型磁性开关|SMC|D-F8BL|线长3M",
            part: "1950120032473A",
            station: "F020",
            source: "FLEX"
        },
        {
            name: "圆形磁性感应器",
            part: "1950120020814A",
            station: "",
            source: "FLEX"
        },
        {
            name: "方型磁性感应器",
            part: "1950100010334A",
            station: "",
            source: "FLEX"
        },
        {
            name: "惰轮|国产|AHTF16S5M100-FC27\n同步轮|米思米|AHTF16S5M100-FC26",
            part: "1950020053249A",
            station: "科瑞恩流道",
            source: "FLEX"
        },
        {
            name: "惰轮|国产|AHTF16S5M100-FC27\n同步轮|米思米|AHTF16S5M100-FC26",
            part: "1950020052303A",
            station: "科瑞恩流道",
            source: "FLEX"
        },
        {
            name: "吸盘|国产|QVP4RNL|H36-H553站吸笔吸盘|黑色",
            part: "1950120037867A",
            station: "C020",
            source: "FLEX"
        }
    ];

    // ============================================================
    // 状态变量
    // ============================================================

    let panelOpen = true;

    // 当前网页最后一次点击的输入框
    let lastInput = null;

    // 拖动状态
    let dragging = false;

    let dragStartX = 0;
    let dragStartY = 0;

    let startLeft = 0;
    let startTop = 0;

    let moved = false;

    // ============================================================
    // 记住用户最后点击的网页输入框
    //
    // 注意：
    // 悬浮窗里面的输入框不会被记录。
    // ============================================================

    document.addEventListener('focusin', (e) => {

        const el = e.target;

        if (
            el &&
            (
                el.tagName === 'INPUT' ||
                el.tagName === 'TEXTAREA'
            ) &&
            !el.closest('#ict-consumable-helper')
        ) {
            lastInput = el;
        }

    }, true);


    // ============================================================
    // 创建样式
    // ============================================================

    const style = document.createElement('style');

    style.textContent = `

        /* ========================================================
           主悬浮窗
           ======================================================== */

        #ict-consumable-helper {

            position: fixed;

            z-index: 2147483647;

            top: 110px;

            right: 0;

            width: 340px;

            font-family:
                -apple-system,
                BlinkMacSystemFont,
                "SF Pro Display",
                "Segoe UI",
                Arial,
                sans-serif;

            user-select: none;

            transition:
                transform .25s ease,
                width .2s ease;

            filter:
                drop-shadow(
                    0 8px 24px rgba(0,0,0,.18)
                );
        }


        /* ========================================================
           左侧状态
           ======================================================== */

        #ict-consumable-helper.ict-left {

            left: 0;

            right: auto;
        }


        /* ========================================================
           右侧状态
           ======================================================== */

        #ict-consumable-helper.ict-right {

            right: 0;

            left: auto;
        }


        /* ========================================================
           最小化状态
           ======================================================== */

        #ict-consumable-helper.ict-minimized {

            width: 54px;
        }


        /* ========================================================
           卡片
           ======================================================== */

        .ict-card {

            overflow: hidden;

            background:
                rgba(255,255,255,.96);

            border:
                1px solid rgba(0,0,0,.10);

            border-radius:
                0 16px 16px 0;

            box-shadow:
                0 12px 35px rgba(0,0,0,.12);

            backdrop-filter:
                blur(20px);
        }


        /* ========================================================
           右侧卡片圆角
           ======================================================== */

        #ict-consumable-helper.ict-right .ict-card {

            border-radius:
                16px 0 0 16px;
        }


        /* ========================================================
           顶部标题栏
           ======================================================== */

        .ict-header {

            height: 48px;

            display: flex;

            align-items: center;

            padding:
                0 10px 0 14px;

            cursor: move;

            background:
                linear-gradient(
                    135deg,
                    #1677ff,
                    #4096ff
                );

            color: white;
        }


        /* ========================================================
           标题
           ======================================================== */

        .ict-title {

            flex: 1;

            font-size: 15px;

            font-weight: 700;

            white-space: nowrap;
        }


        /* ========================================================
           数量
           ======================================================== */

        .ict-count {

            margin-left: 7px;

            font-size: 11px;

            opacity: .82;

            font-weight: 500;
        }


        /* ========================================================
           收起按钮
           ======================================================== */

        .ict-btn {

            width: 30px;

            height: 30px;

            border: 0;

            border-radius: 9px;

            color: white;

            background:
                rgba(255,255,255,.16);

            cursor: pointer;

            font-size: 18px;

            line-height: 30px;
        }


        .ict-btn:hover {

            background:
                rgba(255,255,255,.28);
        }


        /* ========================================================
           内容区域
           ======================================================== */

        .ict-body {

            padding: 10px;
        }


        /* ========================================================
           搜索框
           ======================================================== */

        .ict-search {

            user-select: text !important;

            -webkit-user-select: text !important;

            pointer-events: auto !important;

            position: relative;

            z-index: 2;

            width: 100%;

            box-sizing: border-box;

            border:
                1px solid #d9d9d9;

            border-radius: 10px;

            padding:
                10px 12px;

            outline: none;

            font-size: 14px;

            background:
                #f7f8fa;
        }


        .ict-search:focus {

            border-color:
                #1677ff;

            background:
                white;

            box-shadow:
                0 0 0 3px
                rgba(22,119,255,.10);
        }


        /* ========================================================
           提示文字
           ======================================================== */

        .ict-tip {

            padding:
                9px 4px 7px;

            color:
                #888;

            font-size:
                11px;
        }


        /* ========================================================
           列表
           ======================================================== */

        .ict-list {

            max-height:
                440px;

            overflow-y:
                auto;

            padding-right:
                2px;
        }


        /* ========================================================
           单个耗品
           ======================================================== */

        .ict-item {

            padding:
                10px;

            margin-bottom:
                7px;

            border-radius:
                10px;

            border:
                1px solid #eeeeee;

            background:
                white;

            cursor:
                pointer;

            transition:
                all .15s ease;
        }


        .ict-item:hover {

            transform:
                translateX(-2px);

            border-color:
                #91caff;

            background:
                #f0f7ff;
        }


        /* ========================================================
           耗品名称
           ======================================================== */

        .ict-name {

            font-size:
                13px;

            font-weight:
                650;

            color:
                #222;

            line-height:
                1.35;

            word-break:
                break-all;
        }


        /* ========================================================
           料号
           ======================================================== */

        .ict-part {

            margin-top:
                5px;

            font-size:
                14px;

            font-family:
                Consolas,
                "SF Mono",
                monospace;

            color:
                #1677ff;

            font-weight:
                700;
        }


        /* ========================================================
           工站信息
           ======================================================== */

        .ict-meta {

            margin-top:
                4px;

            font-size:
                11px;

            color:
                #999;
        }


        /* ========================================================
           没有搜索结果
           ======================================================== */

        .ict-empty {

            padding:
                35px 10px;

            text-align:
                center;

            color:
                #999;

            font-size:
                13px;
        }


        /* ========================================================
           Toast 提示
           ======================================================== */

        .ict-toast {

            position:
                fixed;

            z-index:
                2147483647;

            left:
                50%;

            top:
                25px;

            transform:
                translateX(-50%)
                translateY(-20px);

            background:
                rgba(0,0,0,.78);

            color:
                white;

            padding:
                9px 15px;

            border-radius:
                10px;

            font-size:
                13px;

            opacity:
                0;

            pointer-events:
                none;

            transition:
                .2s;
        }


        .ict-toast.show {

            opacity:
                1;

            transform:
                translateX(-50%)
                translateY(0);
        }


        /* ========================================================
           最小化时隐藏内容
           ======================================================== */

        #ict-consumable-helper.ict-minimized .ict-body,
        #ict-consumable-helper.ict-minimized .ict-title,
        #ict-consumable-helper.ict-minimized .ict-count {

            display:
                none;
        }


        /* ========================================================
           最小化标题栏
           ======================================================== */

        #ict-consumable-helper.ict-minimized .ict-header {

            padding:
                0;

            justify-content:
                center;

            border-radius:
                16px 0 0 16px;

            cursor:
                pointer;
        }


        /* ========================================================
           左侧最小化圆角
           ======================================================== */

        #ict-consumable-helper.ict-minimized.ict-left .ict-header {

            border-radius:
                0 16px 16px 0;
        }


        /* ========================================================
           最小化按钮
           ======================================================== */

        #ict-consumable-helper.ict-minimized .ict-btn {

            background:
                transparent;

            font-size:
                21px;
        }


        /* ========================================================
           滚动条
           ======================================================== */

        .ict-list::-webkit-scrollbar {

            width:
                6px;
        }


        .ict-list::-webkit-scrollbar-thumb {

            background:
                #d0d0d0;

            border-radius:
                10px;
        }

    `;

    document.head.appendChild(style);


    // ============================================================
    // 创建悬浮窗
    // ============================================================

    const helper = document.createElement('div');

    helper.id =
        'ict-consumable-helper';

    helper.className =
        'ict-right';


    helper.innerHTML = `

        <div class="ict-card">

            <div class="ict-header">

                <div class="ict-title">

                    📦 耗品快速领取

                    <span class="ict-count">
                        ${CONSUMABLES.length}项
                    </span>

                </div>

                <button
                    class="ict-btn"
                    id="ict-toggle"
                    title="收起/展开"
                >
                    −
                </button>

            </div>


            <div class="ict-body">

                <input
                    id="ict-search"
                    class="ict-search"
                    placeholder="搜索耗品名称、料号、工站..."
                    autocomplete="off"
                >


                <div class="ict-tip">

                    点击耗品后自动填入当前领取页面的料号输入框

                </div>


                <div
                    id="ict-list"
                    class="ict-list"
                ></div>

            </div>

        </div>

    `;

    document.body.appendChild(helper);


    // ============================================================
    // 获取控件
    // ============================================================

    const searchInput =
        helper.querySelector('#ict-search');

    const list =
        helper.querySelector('#ict-list');

    const toggleBtn =
        helper.querySelector('#ict-toggle');

    const header =
        helper.querySelector('.ict-header');


    // ============================================================
    // Toast 提示
    // ============================================================

    function toast(text) {

        let t =
            document.querySelector('.ict-toast');


        if (!t) {

            t =
                document.createElement('div');

            t.className =
                'ict-toast';

            document.body.appendChild(t);
        }


        t.textContent =
            text;


        t.classList.add('show');


        clearTimeout(t._timer);


        t._timer =
            setTimeout(
                () => t.classList.remove('show'),
                1800
            );
    }


    // ============================================================
    // 查找领取页面中的料号输入框
    //
    // 优先：
    // 1. 用户最后点击的输入框
    // 2. 根据料号相关关键词寻找
    // 3. 页面第一个可用输入框
    // ============================================================

    function findMaterialInput() {

        if (
            lastInput &&
            document.contains(lastInput) &&
            !lastInput.disabled &&
            !lastInput.readOnly
        ) {
            return lastInput;
        }


        const inputs = [
            ...document.querySelectorAll(
                'input:not([type="hidden"]):not([disabled]):not([readonly])'
            )
        ];


        const keywords = [
            '料号',
            '物料号',
            '物料编码',
            'material',
            'part',
            'item'
        ];


        const candidate =
            inputs.find(input => {

                const attrs = [

                    input.placeholder,

                    input.name,

                    input.id,

                    input.getAttribute(
                        'aria-label'
                    ),

                    input.getAttribute(
                        'title'
                    )

                ]
                .filter(Boolean)
                .join(' ')
                .toLowerCase();


                let labelText = '';


                if (input.id) {

                    try {

                        const label =
                            document.querySelector(
                                `label[for="${CSS.escape(input.id)}"]`
                            );

                        if (label) {

                            labelText =
                                label.textContent || '';
                        }

                    } catch (_) {}
                }


                return keywords.some(k =>

                    attrs.includes(
                        k.toLowerCase()
                    )

                    ||

                    labelText.includes(k)

                );

            });


        return candidate ||
            inputs[0] ||
            null;
    }


    // ============================================================
    // React / Vue / 原生输入框赋值
    // ============================================================

    function setNativeValue(target, value) {

        const proto =
            target.tagName === 'TEXTAREA'
                ? window.HTMLTextAreaElement.prototype
                : window.HTMLInputElement.prototype;


        const setter =
            Object.getOwnPropertyDescriptor(
                proto,
                'value'
            )?.set;


        if (setter) {

            setter.call(
                target,
                value
            );

        } else {

            target.value =
                value;
        }


        // 触发网页监听

        target.dispatchEvent(
            new Event(
                'input',
                {
                    bubbles: true
                }
            )
        );


        target.dispatchEvent(
            new Event(
                'change',
                {
                    bubbles: true
                }
            )
        );
    }


    // ============================================================
    // 填入料号
    //
    // 支持：
    // 单个料号
    // 多个料号连续追加
    //
    // 例如：
    //
    // 1950120030036A
    //
    // 再点击另一个：
    //
    // 1950120030036A,1950110050K12A
    //
    // 再点击：
    //
    // 1950120030036A,1950110050K12A,1950130090504A
    //
    // 已存在的料号不会重复添加。
    // ============================================================

    function fillMaterialNumber(part) {

        const target =
            findMaterialInput();


        // 找不到输入框

        if (!target) {

            if (
                typeof GM_setClipboard ===
                'function'
            ) {

                GM_setClipboard(part);

            } else {

                navigator.clipboard?.writeText(part);
            }


            toast(
                '未找到料号输入框，料号已复制'
            );

            return;
        }


        target.focus();


        const oldValue =
            String(
                target.value || ''
            ).trim();


        // TEXTAREA 使用换行
        // INPUT 使用逗号

        const separator =
            target.tagName === 'TEXTAREA'
                ? '\n'
                : ',';


        // 解析原有料号

        const values =
            oldValue
                ? oldValue
                    .split(
                        /[\n,，;；\s]+/
                    )
                    .filter(Boolean)
                : [];


        // 防止重复添加

        if (!values.includes(part)) {

            values.push(part);
        }


        // 写回输入框

        setNativeValue(
            target,
            values.join(separator)
        );


        // 记住当前输入框

        lastInput =
            target;


        // 提示

        toast(
            values.length > 1

                ? `已加入料号：${part}（共${values.length}个）`

                : `已填入料号：${part}`
        );
    }


    // ============================================================
    // 渲染耗品列表
    // ============================================================

    function renderList(keyword = '') {

        const key =
            keyword
                .trim()
                .toLowerCase();


        const result =
            !key

                ? CONSUMABLES

                : CONSUMABLES.filter(
                    item =>

                        item.name
                            .toLowerCase()
                            .includes(key)

                        ||

                        item.part
                            .toLowerCase()
                            .includes(key)

                        ||

                        item.station
                            .toLowerCase()
                            .includes(key)

                        ||

                        item.source
                            .toLowerCase()
                            .includes(key)
                );


        // 没有结果

        if (!result.length) {

            list.innerHTML =
                '<div class="ict-empty">没有找到对应耗品</div>';

            return;
        }


        list.innerHTML =
            '';


        // 最多显示100条

        result
            .slice(0, 100)
            .forEach(item => {

                const el =
                    document.createElement(
                        'div'
                    );


                el.className =
                    'ict-item';


                const meta = [

                    item.source,

                    item.station
                        ? `工站：${item.station}`
                        : ''

                ]
                .filter(Boolean)
                .join(' · ');


                el.innerHTML = `

                    <div class="ict-name">

                        ${escapeHtml(item.name)}

                    </div>


                    <div class="ict-part">

                        ${escapeHtml(item.part)}

                    </div>


                    <div class="ict-meta">

                        ${escapeHtml(meta)}

                    </div>

                `;


                // 点击耗品

                el.addEventListener(
                    'click',
                    () => {

                        fillMaterialNumber(
                            item.part
                        );

                    }
                );


                list.appendChild(el);

            });
    }


    // ============================================================
    // HTML 安全处理
    // ============================================================

    function escapeHtml(str) {

        return String(str)

            .replace(
                /&/g,
                '&amp;'
            )

            .replace(
                /</g,
                '&lt;'
            )

            .replace(
                />/g,
                '&gt;'
            )

            .replace(
                /"/g,
                '&quot;'
            )

            .replace(
                /'/g,
                '&#039;'
            );
    }


    // ============================================================
    // 防止网页/拖动逻辑抢走搜索框焦点
    //
    // 这部分就是解决：
    // 「多料号输入框无法输入」
    // 「搜索框点击后无法打字」
    // ============================================================

    [
        'mousedown',
        'mouseup',
        'click',
        'dblclick',
        'keydown',
        'keyup',
        'keypress'
    ].forEach(type => {

        searchInput.addEventListener(
            type,
            e => e.stopPropagation(),
            true
        );

    });


    // 搜索

    searchInput.addEventListener(
        'input',
        () => {

            renderList(
                searchInput.value
            );

        }
    );


    // ============================================================
    // 收起 / 展开
    // ============================================================

    toggleBtn.addEventListener(
        'click',
        (e) => {

            e.stopPropagation();


            panelOpen =
                !panelOpen;


            helper.classList.toggle(
                'ict-minimized',
                !panelOpen
            );


            toggleBtn.textContent =
                panelOpen
                    ? '−'
                    : '☰';

        }
    );


    // ============================================================
    // 最小化状态下点击标题栏恢复
    // ============================================================

    header.addEventListener(
        'click',
        (e) => {

            if (
                helper.classList.contains(
                    'ict-minimized'
                )

                &&

                !dragging

                &&

                !moved
            ) {

                panelOpen =
                    true;


                helper.classList.remove(
                    'ict-minimized'
                );


                toggleBtn.textContent =
                    '−';
            }

        }
    );


    // ============================================================
    // 拖动悬浮窗
    //
    // 使用 Pointer Events
    // 鼠标 / 触控板均可
    //
    // 拖动结束后自动吸附左边或右边
    // ============================================================

    function startDrag(e) {

        // 点击按钮、输入框等控件时不拖动

        if (
            e.target.closest(
                'button, input, textarea, select, option'
            )
        ) {
            return;
        }


        // 只允许鼠标左键

        if (
            e.button !== undefined &&
            e.button !== 0
        ) {
            return;
        }


        dragging =
            true;


        moved =
            false;


        const rect =
            helper.getBoundingClientRect();


        dragStartX =
            e.clientX;


        dragStartY =
            e.clientY;


        startLeft =
            rect.left;


        startTop =
            rect.top;


        // 拖动时切换为绝对坐标

        helper.style.left =
            startLeft + 'px';


        helper.style.right =
            'auto';


        helper.style.top =
            startTop + 'px';


        // 删除左右吸附状态

        helper.classList.remove(
            'ict-left',
            'ict-right'
        );


        // 捕获 Pointer

        try {

            header.setPointerCapture?.(
                e.pointerId
            );

        } catch (_) {}


        // 防止浏览器默认拖动/选择

        e.preventDefault();
    }


    // ============================================================
    // 拖动中
    // ============================================================

    function moveDrag(e) {

        if (!dragging) {
            return;
        }


        const dx =
            e.clientX -
            dragStartX;


        const dy =
            e.clientY -
            dragStartY;


        if (
            Math.abs(dx) > 3 ||
            Math.abs(dy) > 3
        ) {

            moved =
                true;
        }


        // 最大 X

        const maxLeft =
            Math.max(
                0,
                window.innerWidth -
                helper.offsetWidth
            );


        // 最大 Y

        const maxTop =
            Math.max(
                0,
                window.innerHeight -
                helper.offsetHeight
            );


        // 新位置

        const newLeft =
            Math.max(
                0,
                Math.min(
                    maxLeft,
                    startLeft + dx
                )
            );


        const newTop =
            Math.max(
                0,
                Math.min(
                    maxTop,
                    startTop + dy
                )
            );


        helper.style.left =
            newLeft + 'px';


        helper.style.top =
            newTop + 'px';
    }


    // ============================================================
    // 拖动结束
    // ============================================================

    function endDrag() {

        if (!dragging) {
            return;
        }


        dragging =
            false;


        const rect =
            helper.getBoundingClientRect();


        const centerX =
            rect.left +
            rect.width / 2;


        helper.style.transition =
            'all .25s ease';


        // 左半边 -> 吸附左边

        if (
            centerX <
            window.innerWidth / 2
        ) {

            helper.classList.add(
                'ict-left'
            );


            helper.classList.remove(
                'ict-right'
            );


            helper.style.left =
                '0px';


            helper.style.right =
                'auto';


        // 右半边 -> 吸附右边

        } else {

            helper.classList.add(
                'ict-right'
            );


            helper.classList.remove(
                'ict-left'
            );


            helper.style.right =
                '0px';


            helper.style.left =
                'auto';
        }


        // 恢复默认 transition

        setTimeout(
            () => {

                helper.style.transition =
                    '';

            },
            280
        );
    }


    // ============================================================
    // 注册拖动事件
    // ============================================================

    header.addEventListener(
        'pointerdown',
        startDrag
    );


    window.addEventListener(
        'pointermove',
        moveDrag
    );


    window.addEventListener(
        'pointerup',
        endDrag
    );


    window.addEventListener(
        'pointercancel',
        endDrag
    );


    // ============================================================
    // 浏览器窗口尺寸变化
    // 防止悬浮窗跑出屏幕
    // ============================================================

    window.addEventListener(
        'resize',
        () => {

            const rect =
                helper.getBoundingClientRect();


            const maxTop =
                Math.max(
                    0,
                    window.innerHeight -
                    helper.offsetHeight
                );


            if (
                rect.top >
                maxTop
            ) {

                helper.style.top =
                    maxTop + 'px';
            }

        }
    );


    // ============================================================
    // 初始渲染
    // ============================================================

    renderList();

})();