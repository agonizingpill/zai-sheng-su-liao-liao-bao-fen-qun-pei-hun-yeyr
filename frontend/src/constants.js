export const ROLES={admin:'投料主管',blender:'配混员',viewer:'质检观察员'};
export const BLEND_STATES={draft:'待称料',ready:'审秤通过',released:'已投料'};
export const AUDIT_ACTIONS={bale_received:'来料登记',bale_retested:'料包复检',blend_created:'配方立单',weighed:'称料保存',checked:'审秤通过',blend_reopened:'退回秤台',released:'主管投料放行',assign_applied:'归群批次判定',assign_voided:'归群批次作废'};

export const LOT_STATES={active:'来料可用',quarantine:'整批隔离'};
export const PELLET_STATES={quarantine:'PVC越限隔离',passed:'检验合格待签证',certified:'主管已发合格证'};

export const DRYING_STATES={drying:'烘干中',redry:'超含水待延烘',passed:'含水合格待验收',accepted:'主管已验收'};
export const PACK_STATES={open:'未封可调整',sealed:'已封箱',cancelled:'未封取消',loaded:'已装车冻结'};
export const SHIPMENT_STATES={loading:'装车中',dispatched:'已发车',received:'客户已签收'};
export const ASSIGN_STATES={assigned:'归群通过',pending_recheck:'待复检',applied:'判定完成',voided:'整批作废'};
