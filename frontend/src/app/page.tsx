import { redirect } from "next/navigation";

/**
 * 根路径默认跳转到 v0.1.0 主模块：法规问答（agent search）.
 * v0.2+ 上线凭证录入后视情况调整默认.
 */
export default function Home() {
  redirect("/regulations");
}
