import { useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../store/auth';

/**
 * 角色感知的导航 Hook。
 *
 * 根据当前登录用户的角色，将路由路径映射到角色对应的目标页面。
 * LoginPage 和 App.tsx 共用此 Hook，消除重复的 role→path 映射逻辑。
 *
 * 用法示例：
 * ```
 * const go = useRoleNavigate();
 * go();              // 无参 → 跳转到角色默认页
 * go('/coach');      // 传入路径 → 检查角色权限后跳转（无权限则跳回默认页）
 * ```
 */

type Role = 'admin' | 'coach' | 'trainee';

const ROLE_HOME: Record<Role, string> = {
  admin: '/admin',
  coach: '/coach',
  trainee: '/home',
};

/** 角色可访问的路由白名单 */
const ROLE_ACCESS: Record<Role, string[]> = {
  admin: ['/admin', '/coach', '/coach/actions', '/home'],
  coach: ['/coach', '/coach/actions', '/home'],
  trainee: ['/home'],
};

export function roleToPath(role: string | undefined): string {
  return ROLE_HOME[role as Role] || '/home';
}

export default function useRoleNavigate() {
  const navigate = useNavigate();
  const user = useAuthStore(s => s.user);

  const go = useCallback(
    (path?: string) => {
      const role = user?.role as Role | undefined;
      if (path) {
        // 显式传入路径：检查角色是否有权访问
        const allowed = role ? ROLE_ACCESS[role] : [];
        navigate(allowed.includes(path) ? path : roleToPath(role));
      } else {
        // 无参：跳转到角色默认页
        navigate(roleToPath(role));
      }
    },
    [navigate, user?.role],
  );

  return go;
}
