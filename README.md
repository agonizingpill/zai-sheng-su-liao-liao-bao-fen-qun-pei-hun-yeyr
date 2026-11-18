# 环粒 · 再生塑料料包分群与配混

让检验过的 PET 料包按性状选料，称量配方并核对 PVC，主管放行时逐包扣减重量，再核烘干含水、成品签证、箱码包装和装车签收。

模拟客户环粒再生有28名回收再造人员。现在检验员在纸签写熔指、水分、氯含量，配混员凭颜色和熔指挑包，主管口头通知投料。三项痛点是不同熔指混放、PVC风险被忽略、秤台总重与堆场余量不一致。上游是入场检验记录，本项目替代选料、配混审核和交接，下游挤出班得到已签署投料单及剩余料包重量。

## 快速启动

```bash
cp .env.example .env
docker compose up -d --build --wait
# SEED_DEMO=true 默认启动seed；手动重跑也安全
docker compose exec -T backend python -m scripts.seed_demo
```

访问前端 http://localhost:18225 ，API http://localhost:19225/docs ，MySQL localhost:17725。收尾 `docker compose down -v --remove-orphans` 会删除本项目演示卷。

|角色|账号|口令|主要动作|
|---|---|---|---|
|admin 投料主管|admin@huanli.local|Blend2026!|全部操作、最终投料放行、供应批隔离/解除、烘干验收、成品证书签发、发车冻结清单|
|blender 配混员|blender@huanli.local|Blend2026!|检验、分群、立单、称料、审秤、待放行单退回；供应批挂包、粒料取样与隔离复检、烘干安排/复测、包装称重/封箱、客户签收；无最终投料及发证权限|
|viewer 质检观察员|viewer@huanli.local|Blend2026!|只读九个页面及交接轨迹|

## 业务流程与约束

1. 料包堆场登记编号、原始kg、熔指、水分、PVC。编号唯一；可用量不小于零且不超过原始重量。
2. 可混群落由Python worker实际计算，输入三项检验特征。未分群新料不能直接称入。
3. 配混秤台立单目标kg与PVC上限；每份称料行关联配方与料包，保存**群号、分群版本及质量快照**。同包不可重复，保存时就拒绝超过当前可用量。
4. 审秤校验同版本同群、总重等于目标、Σ(重量×PVC)/总重≤上限、每包可用量足够；全部通过进入ready。审秤不扣料。
5. 主管放行先锁配方，再按料包ID顺序`SELECT FOR UPDATE`；重新校验余量后，在一个事务扣减所有料包，配方变released并保存签署人。任一失败整体回滚。重复放行、已放行改单和退回都拒绝。

6. 供应隔离复核：新批次记录供应商与首检依据；料包归属唯一，记录入批质量快照。主管隔离/解除必须填写至少8字依据。隔离批次阻止配方新审秤和已经ready配方最终投料；检查在原配混事务内生效。挂批、隔离和投料按料包→供应批顺序锁定。已投料料包禁止事后补挂，避免改变追溯。历史未挂批料仍保留原流程兼容性。
7. 粒料检验放行：仅released配方取样，产出不得超过实际投料，MI必须正值；PVC大于原配方上限记录quarantine，合格记passed。隔离料可按依据追加复检，首次异常不覆盖。主管只可对passed记录发唯一HL-CERT证书，保存投料/称料/质量/来源与最新检验快照，之后不可重复发证或复检覆盖。

8. 烘干含水复检：主管登记Dryer设备，released配方开DryingRun，设备行锁核时段，配方唯一作业；投入含水由称料质量快照加权计算。含水>0.05%记redry，延烘结束不可倒退且须重查设备后续占用；复测≤0.05%记passed，主管验收accepted后才允许成品新签证，证书加入烘干快照；旧certified不重算。
9. 包装箱码追溯：certified成品按唯一箱码分包，锁同成品校验有效包装累计≤actual_kg；open可改重或取消释放额度，sealed后冻结，证书快照随箱保存。已装车仍计入累计，避免重复包装同一产出。
10. 装车客户签收：同车只能装同配方sealed箱，ShipmentPack.pack_id唯一，加载后包状态loaded阻止再次出库；主管发车保存冻结manifest。实收与清单差率绝对值>0.5%须至少8字依据，记录客户签收快照后不得重复签收。仅本地记录交接，无实际运输消息。

已被任何配方引用的料包质量/原始重量不得修改；可用量只在放行扣减。重做全场分群会更新堆场当前群号，既有配方继续使用原称料时的质量/群号快照。对旧快照配方添加新版本料包会被审秤拦截，需退回并整体重新称料。

### 一天的工作剧本

08:30检验员核对PET-117/118，原始与可用均500kg；09:00配混员为45包运行分群；09:30在BL-20261117分别称入200kg、200kg，目标400kg，PVC门限40ppm；10:00审秤通过；10:30故意跨群配料，被拒并且余量不变；11:00查看PVC门限5ppm配方超限，不允许投料；14:00主管放行BL-20261117，两包各剩300kg；15:00两份400kg配方同时争用PET-119的500kg，只有一份能放行，剩100kg；16:00交接簿查看签署与冻结记录。

17:00在「供应隔离复核」查看SL-ACCEPT-17（PET-129可用）与SL-HOLD-17（PET-131隔离），将新批SL-03关联PET-124；先审秤后隔离，再尝试最终投料，应实时拒绝且不扣料。主管按复检说明解除后方可投料。17:30已投料100kg配方的成品取样96kg、MI9.1、PVC65ppm，超过40ppm记隔离；清线复检24ppm，主管发合格证。初次65ppm、复检24ppm和投料快照全部保留。

V3演练：11月24日DRY-B接BL-PELLET-UI的100kg投料，08:00—12:00烘干；实测0.04%，主管验收后成品96kg/20ppm才签证。包装PK-BROWSER-V3为25kg，封箱后放入SH-BROWSER-V3，客户华远注塑一号原料库，主管发车，客户签24.9kg，差率-0.4%保存。API另演练0.08%延烘、撞时段拒绝、包装超重/取消释放及超签收差异说明。

## 真实ML计算

`StandardScaler`对熔指、水分和PVC标准化，`KMeans(n_clusters=3,n_init=10,random_state=42)`聚类，输出每包标签、原量纲群中心、inertia与轮廓系数。群号按中心熔指从低到高排序。输入按料包ID排序，seed42可复现。至少6包且至少3种不同特征；不足时拒绝并保留现有结果。轮廓系数是当前无监督分群的结构描述，不是训练/留出预测准确率。演示seed45包分三种材料范围；实际检验数据未接入，不能把演示分群质量当作实际投料质量保证，配方PVC和重量门限仍是后端硬约束。

## 技术栈与目录

|层|实现|
|---|---|
|前端|原生HTML/CSS/ES modules，Nginx1.27，双字体、工业材料标签布局|
|API|Python3.12/FastAPI/SQLAlchemy2/PyMySQL|
|算法|scikit-learn1.6/NumPy，Redis7队列独立worker|
|数据库|MySQL8，Decimal重量和ppm，外键、唯一键、范围约束，64位分群版本|
|横切|JWT8小时、PBKDF2口令、三角色、业务审计、请求追踪、全局错误恢复|

`backend/src/models.py`：Bale、Blend、BlendPortion；`schemas.py`：字段范围；`blending.py`：称料、审秤、放行事务；`clustering.py`：实际算法；`worker.py`：队列与心跳；`main.py`：路由；`middlewares.py`：追踪/恢复。`backend/scripts/seed_demo.py`自然键只插入缺失演示记录，重复seed保留用户修改。

`backend/src/quality_models.py`：SupplierLot/LotBale/PelletCheck；`quality_schemas.py`：批次、决策、取样与复检字段；`quality_service.py`：追溯挂批/主管隔离、质量平衡、历次检验与证书快照；`quality_routes.py`：`/supplier-lots` 与 `/pellet-checks`（含bales/quarantine/clear/retest/certify）。新建三张表，不修改原表列，已有数据通过create_all扩展，无破坏性迁移。

V3 `backend/src/production_models.py`定义Dryer/DryingRun/PelletPack/BlendShipment/ShipmentPack；`production_schemas.py`校验时间、含水、称重与客户收货；`production_service.py`设备锁/时段重叠、累计包装锁、装车唯一和签收差率；`production_routes.py`提供`/dryers`、`/drying-runs`、`/pellet-packs`、`/blend-shipments`。新加5张表，原表列无变更，create_all兼容历史记录。

`frontend/src/pages/yard.js`堆场；`clusters.js`真实散点与中心；`bench.js`可增删称料行；`release.js`交接簿；`lots.js`供应隔离复核；`pellets.js`粒料检验与证书；`drying.js`含水复检；`packs.js`包装箱码；`shipments.js`装车客户签收。`components/labels.js`共享群标签、状态条、标签页、标题与通知，群标签在图谱、秤台与放行中复用。`utils/api.js`会话/接口/store，`utils/format.js`数字/转义/上海时区。角色、配方状态、供应批、成品检验、烘干、包装和装车状态枚举定义在`backend/src/constants.py`、`frontend/src/constants.js`，状态实际转移在`blending.py`与`main.py`，标签渲染在`components/labels.js`。

Compose恰好frontend/backend/worker/db/redis五服务，全部healthcheck。MySQL健康检查采用127.0.0.1业务账号SELECT1，避开初始化临时socket；前端和后端也用127.0.0.1。数据库、Redis和模型文件/心跳分别为命名卷。宿主默认地址池已用尽，本项目显式10.221.26.0/24；换环境冲突时调整networks。环境变量见.env.example：COMPOSE_PROJECT_NAME、FRONTEND_PORT、BACKEND_PORT、DB_PORT、JWT_SECRET。内网DATABASE_URL/REDIS_URL/SEED_DEMO由Compose设置。

本地开发：在backend目录`pip install -r requirements.txt`，设置MySQL/Redis连接后`uvicorn src.main:app --reload`；前端由Nginx代理API。测试与截图单独放在外层`test-artifacts/gb-1026`，不会混入源码。

## 已知范围

模拟45包检验资料，不接地磅/化验仪；无物理投料设备联动。配方与成品以PVC、重量平衡为硬门限，成品记录正值MI，未加入具体产品应用的MI/水分区间。供应来料隔离不追溯撤销已经投料和已经签发的成品证书；历史快照保留。成品包装与装车在本地记录受控出库清单，不接外部仓储或销售财务。烘干每配方一单，含水按实际取样手录，不接设备传感器或能耗表；设备时段包括已验收历史，不能重叠回填。未实现封箱拆包/已发车撤销，避免不受控重复出库。一个worker、Redis list；取任务后worker异常退出无可靠重投。每次聚类在全场已检验料包上计算，分群是辅助选料，不替代检测。历史已放行配方不可撤销，避免演示中不受控返库。演示JWT secret与账号密码在正式部署前更换。

License: MIT.
