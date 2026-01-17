import React, { useState, useEffect } from 'react';
import styled, { keyframes } from 'styled-components';
import { logout, clearAuth } from '../api/auth';
import { getAuditLogs, listUsers, updateUser, revokeUserSessions, listActiveSessions, revokeSession } from '../api/admin';

/**
 * BioMind Nexus Admin Dashboard
 * 
 * Admin-only interface for:
 * - Viewing audit logs
 * - Managing users
 * - Monitoring active sessions
 */

// ============================================
// Animations
// ============================================
const fadeIn = keyframes`
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
`;

const float = keyframes`
  0% { transform: translate(0px, 0px); }
  50% { transform: translate(10px, -10px); }
  100% { transform: translate(0px, 0px); }
`;

const spin = keyframes`
  to { transform: rotate(360deg); }
`;

// ============================================
// Layout Components
// ============================================

const DashboardContainer = styled.div`
  display: flex;
  min-height: 100vh;
  background-color: #f1f5f9;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  position: relative;

  background-image: 
    linear-gradient(rgba(71, 85, 105, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(71, 85, 105, 0.08) 1px, transparent 1px);
  background-size: 32px 32px;

  &::before {
    content: '';
    position: fixed;
    top: -10%;
    right: -5%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(234, 88, 12, 0.08) 0%, transparent 70%);
    border-radius: 50%;
    filter: blur(80px);
    animation: ${float} 12s ease-in-out infinite;
    z-index: 0;
    pointer-events: none;
  }
`;

const Sidebar = styled.aside`
  width: 280px;
  background: linear-gradient(180deg, #1e293b 0%, #0f172a 100%);
  color: white;
  display: flex;
  flex-direction: column;
  padding: 2rem 0;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;
`;

const SidebarBrand = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 1.5rem;
  margin-bottom: 2.5rem;

  svg { width: 32px; height: 32px; flex-shrink: 0; }
  span { font-weight: 800; font-size: 1.15rem; letter-spacing: -0.02em; }
`;

const AdminBadge = styled.span`
  background: linear-gradient(135deg, #f97316 0%, #ea580c 100%);
  color: white;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  margin-left: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
`;

const NavSection = styled.nav`
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 0 0.75rem;
`;

const NavItem = styled.button`
  display: flex;
  align-items: center;
  gap: 0.875rem;
  padding: 0.875rem 1rem;
  background: ${props => props.active ? 'rgba(249, 115, 22, 0.15)' : 'transparent'};
  border: none;
  border-radius: 12px;
  color: ${props => props.active ? '#fb923c' : 'rgba(255, 255, 255, 0.7)'};
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  svg { width: 20px; height: 20px; flex-shrink: 0; }
`;

const SidebarFooter = styled.div`
  padding: 1rem 1.5rem;
  border-top: 1px solid rgba(255, 255, 255, 0.1);
  margin-top: auto;
`;

const UserInfo = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;

  .avatar {
    width: 40px;
    height: 40px;
    background: linear-gradient(135deg, #f97316, #ea580c);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.95rem;
  }

  .details { flex: 1; overflow: hidden;
    .name { font-weight: 600; font-size: 0.9rem; color: white; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .role { font-size: 0.75rem; color: #fb923c; text-transform: capitalize; }
  }
`;

const LogoutBtn = styled.button`
  background: none;
  border: none;
  color: rgba(255, 255, 255, 0.5);
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s;

  &:hover { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
  svg { width: 18px; height: 18px; }
`;

const MainContent = styled.main`
  flex: 1;
  margin-left: 280px;
  padding: 2rem;
  position: relative;
  z-index: 1;
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;
  animation: ${fadeIn} 0.5s ease-out;

  h1 { font-size: 2rem; font-weight: 800; color: #0f172a; letter-spacing: -0.04em; margin: 0 0 0.5rem 0; }
  p { color: #64748b; font-size: 1rem; margin: 0; }
`;

// ============================================
// Card Components
// ============================================

const Card = styled.div`
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 2px 12px -2px rgba(15, 23, 42, 0.06);
  border: 1px solid #e2e8f0;
  animation: ${fadeIn} 0.5s ease-out;
`;

const CardHeader = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.25rem;
  
  h3 { font-size: 1.1rem; font-weight: 700; color: #0f172a; margin: 0; display: flex; align-items: center; gap: 0.5rem; }
`;

const Table = styled.table`
  width: 100%;
  border-collapse: collapse;
  font-size: 0.875rem;
`;

const Th = styled.th`
  text-align: left;
  padding: 0.75rem 1rem;
  font-weight: 600;
  color: #64748b;
  border-bottom: 1px solid #e2e8f0;
  background: #f8fafc;

  &:first-child { border-radius: 8px 0 0 0; }
  &:last-child { border-radius: 0 8px 0 0; }
`;

const Td = styled.td`
  padding: 0.75rem 1rem;
  color: #334155;
  border-bottom: 1px solid #f1f5f9;
`;

const Badge = styled.span`
  display: inline-block;
  padding: 0.25rem 0.625rem;
  font-size: 0.75rem;
  font-weight: 600;
  border-radius: 6px;
  background: ${props => {
        if (props.variant === 'success') return '#dcfce7';
        if (props.variant === 'danger') return '#fef2f2';
        if (props.variant === 'warning') return '#fef3c7';
        if (props.variant === 'admin') return '#fff7ed';
        return '#f1f5f9';
    }};
  color: ${props => {
        if (props.variant === 'success') return '#166534';
        if (props.variant === 'danger') return '#dc2626';
        if (props.variant === 'warning') return '#d97706';
        if (props.variant === 'admin') return '#ea580c';
        return '#475569';
    }};
`;

const ActionBtn = styled.button`
  padding: 0.375rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 500;
  border-radius: 6px;
  border: 1px solid ${props => props.danger ? '#fecaca' : '#e2e8f0'};
  background: ${props => props.danger ? '#fef2f2' : 'white'};
  color: ${props => props.danger ? '#dc2626' : '#475569'};
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background: ${props => props.danger ? '#fee2e2' : '#f1f5f9'};
  }

  &:disabled { opacity: 0.5; cursor: not-allowed; }
`;

const Spinner = styled.div`
  width: 24px;
  height: 24px;
  border: 2px solid #e2e8f0;
  border-top-color: #f97316;
  border-radius: 50%;
  animation: ${spin} 0.8s linear infinite;
  margin: 2rem auto;
`;

const EmptyState = styled.div`
  text-align: center;
  padding: 3rem 2rem;
  color: #64748b;
  
  svg { width: 48px; height: 48px; margin-bottom: 1rem; opacity: 0.5; }
  h4 { font-size: 1rem; font-weight: 600; color: #334155; margin: 0 0 0.25rem 0; }
  p { font-size: 0.875rem; margin: 0; }
`;

// ============================================
// Component
// ============================================

// ... existing imports
import styled, { keyframes, css } from 'styled-components';
// ... api imports

/**
 * BioMind Nexus Admin Dashboard
 */

// ... animations ...

// ============================================
// Styles
// ============================================

// ... (keep existing styles)

const ModalOverlay = styled.div`
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.6);
  backdrop-filter: blur(4px);
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: ${fadeIn} 0.2s ease-out;
`;

const ModalContent = styled.div`
  background: white;
  border-radius: 16px;
  width: 90%;
  max-width: 600px;
  max-height: 85vh;
  box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border: 1px solid #e2e8f0;
`;

const ModalHeader = styled.div`
  padding: 1.25rem 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;

  h3 { margin: 0; font-size: 1.1rem; color: #0f172a; }
`;

const ModalBody = styled.div`
  padding: 1.5rem;
  overflow-y: auto;
`;

const ModalFooter = styled.div`
  padding: 1rem 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  background: #f8fafc;
`;

const JsonPre = styled.pre`
  background: #0f172a;
  color: #e2e8f0;
  padding: 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  overflow-x: auto;
  font-family: 'Fira Code', monospace;
  margin: 0;
`;

const DetailRow = styled.div`
  margin-bottom: 1rem;
  label { display: block; font-size: 0.75rem; color: #64748b; font-weight: 600; margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em; }
  div { font-size: 0.95rem; color: #334155; }
`;

const CloseBtn = styled.button`
    background: none; border: none; cursor: pointer; color: #64748b;
    &:hover { color: #0f172a; }
`;

// ============================================
// Component
// ============================================

export default function AdminDashboard({ user, onLogout }) {
    const [activeView, setActiveView] = useState('audit');
    const [auditLogs, setAuditLogs] = useState([]);
    const [users, setUsers] = useState([]);
    const [sessions, setSessions] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [selectedLog, setSelectedLog] = useState(null);

    // Load data based on active view
    useEffect(() => {
        loadData();
    }, [activeView]);

    const loadData = async () => {
        setIsLoading(true);
        try {
            if (activeView === 'audit') {
                const data = await getAuditLogs({ page: 1, pageSize: 50 });
                setAuditLogs(data.logs || []);
            } else if (activeView === 'users') {
                const data = await listUsers();
                setUsers(data.users || []);
            } else if (activeView === 'sessions') {
                const data = await listActiveSessions();
                setSessions(data.sessions || []);
            }
        } catch (err) {
            console.error('Failed to load data:', err);
        } finally {
            setIsLoading(false);
        }
    };

    const handleLogout = async () => {
        try {
            const token = localStorage.getItem('biomind_access_token');
            const sessionId = localStorage.getItem('biomind_session_id');
            await logout(token, sessionId);
        } catch (err) {
            console.error('Logout error:', err);
        } finally {
            clearAuth();
            onLogout();
        }
    };

    const handleToggleUserStatus = async (userId, currentStatus) => {
        if (!window.confirm(`Are you sure you want to ${currentStatus ? 'deactivate' : 'activate'} this user?`)) return;
        try {
            await updateUser(userId, { is_active: !currentStatus });
            loadData();
        } catch (err) {
            console.error('Failed to update user:', err);
        }
    };

    const handleRevokeUserSessions = async (userId) => {
        if (!window.confirm("This will force the user to log out immediately. Continue?")) return;
        try {
            await revokeUserSessions(userId);
            loadData();
        } catch (err) {
            console.error('Failed to revoke sessions:', err);
        }
    };

    const handleRevokeSession = async (sessionId) => {
        if (!window.confirm("Kill this session?")) return;
        try {
            await revokeSession(sessionId);
            loadData();
        } catch (err) {
            console.error('Failed to revoke session:', err);
        }
    };

    const getInitials = (email) => email ? email.substring(0, 2).toUpperCase() : 'A';

    const formatDate = (dateStr) => {
        if (!dateStr) return '-';
        const date = new Date(dateStr);
        // Explicitly include time zone name if possible, or usually browser default is local
        return date.toLocaleString('en-IN', {
            dateStyle: 'medium',
            timeStyle: 'long',
            hour12: true
        });
    };

    return (
        <DashboardContainer>
            <Sidebar>
                <SidebarBrand>
                    <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                        <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="white" strokeWidth="2.5" />
                        <path d="M8 12L11 15L16 9" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    <span>BioMind Nexus</span>
                    <AdminBadge>Admin</AdminBadge>
                </SidebarBrand>

                <NavSection>
                    <NavItem active={activeView === 'audit'} onClick={() => setActiveView('audit')}>
                        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                        </svg>
                        <span>Audit Logs</span>
                    </NavItem>
                    <NavItem active={activeView === 'users'} onClick={() => setActiveView('users')}>
                        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                        </svg>
                        <span>User Management</span>
                    </NavItem>
                    <NavItem active={activeView === 'sessions'} onClick={() => setActiveView('sessions')}>
                        <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                        </svg>
                        <span>Active Sessions</span>
                    </NavItem>
                </NavSection>

                <SidebarFooter>
                    <UserInfo>
                        <div className="avatar">{getInitials(user?.email)}</div>
                        <div className="details">
                            <div className="name">{user?.email || 'Admin'}</div>
                            <div className="role">Administrator</div>
                        </div>
                        <LogoutBtn onClick={handleLogout} title="Sign out">
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                            </svg>
                        </LogoutBtn>
                    </UserInfo>
                </SidebarFooter>
            </Sidebar>

            <MainContent>
                {/* Audit Logs View */}
                {activeView === 'audit' && (
                    <>
                        <PageHeader>
                            <h1>Audit Logs</h1>
                            <p>View system activity and workflow events</p>
                        </PageHeader>

                        <Card>
                            <CardHeader>
                                <h3>
                                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    Recent Events
                                </h3>
                                <ActionBtn onClick={loadData}>Refresh</ActionBtn>
                            </CardHeader>

                            {isLoading ? (
                                <Spinner />
                            ) : auditLogs.length === 0 ? (
                                <EmptyState>
                                    <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                                    </svg>
                                    <h4>No audit logs yet</h4>
                                    <p>Events will appear here when workflows run</p>
                                </EmptyState>
                            ) : (
                                <Table>
                                    <thead>
                                        <tr>
                                            <Th>Timestamp</Th>
                                            <Th>Event Type</Th>
                                            <Th>User</Th>
                                            <Th>Action</Th>
                                            <Th>Details</Th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {auditLogs.map((log, i) => (
                                            <tr key={log.event_id || i}>
                                                <Td>{formatDate(log.timestamp)}</Td>
                                                <Td><Badge>{log.event_type}</Badge></Td>
                                                <Td title={log.user_id}>{log.user_email || log.user_id.substring(0, 8) + '...'}</Td>
                                                <Td>{log.action}</Td>
                                                <Td>
                                                    <ActionBtn onClick={() => setSelectedLog(log)}>View Details</ActionBtn>
                                                </Td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </Table>
                            )}
                        </Card>
                    </>
                )}

                {/* Users View */}
                {activeView === 'users' && (
                    <>
                        <PageHeader>
                            <h1>User Management</h1>
                            <p>Manage researcher and admin accounts</p>
                        </PageHeader>

                        <Card>
                            <CardHeader>
                                <h3>
                                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
                                    </svg>
                                    All Users
                                </h3>
                                <ActionBtn onClick={loadData}>Refresh</ActionBtn>
                            </CardHeader>

                            {isLoading ? (
                                <Spinner />
                            ) : users.length === 0 ? (
                                <EmptyState>
                                    <h4>No users found</h4>
                                </EmptyState>
                            ) : (
                                <Table>
                                    <thead>
                                        <tr>
                                            <Th>Email</Th>
                                            <Th>Role</Th>
                                            <Th>Status</Th>
                                            <Th>Created</Th>
                                            <Th>Last Login</Th>
                                            <Th>Actions</Th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {users.map((u) => (
                                            <tr key={u.id}>
                                                <Td>{u.email}</Td>
                                                <Td>
                                                    <Badge variant={u.role === 'admin' ? 'admin' : 'default'}>
                                                        {u.role}
                                                    </Badge>
                                                </Td>
                                                <Td>
                                                    <Badge variant={u.is_active ? 'success' : 'danger'}>
                                                        {u.is_active ? 'Active' : 'Inactive'}
                                                    </Badge>
                                                </Td>
                                                <Td>{formatDate(u.created_at)}</Td>
                                                <Td>{u.last_login ? formatDate(u.last_login) : '-'}</Td>
                                                <Td>
                                                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                                                        <ActionBtn
                                                            onClick={() => handleToggleUserStatus(u.id, u.is_active)}
                                                            disabled={u.email === user?.email}
                                                        >
                                                            {u.is_active ? 'Deactivate' : 'Activate'}
                                                        </ActionBtn>
                                                        <ActionBtn
                                                            danger
                                                            onClick={() => handleRevokeUserSessions(u.id)}
                                                        >
                                                            Revoke Sessions
                                                        </ActionBtn>
                                                    </div>
                                                </Td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </Table>
                            )}
                        </Card>
                    </>
                )}

                {/* Sessions View */}
                {activeView === 'sessions' && (
                    <>
                        <PageHeader>
                            <h1>Active Sessions</h1>
                            <p>Monitor and manage active user sessions</p>
                        </PageHeader>

                        <Card>
                            <CardHeader>
                                <h3>
                                    <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 7a2 2 0 012 2m4 0a6 6 0 01-7.743 5.743L11 17H9v2H7v2H4a1 1 0 01-1-1v-2.586a1 1 0 01.293-.707l5.964-5.964A6 6 0 1121 9z" />
                                    </svg>
                                    Current Sessions
                                </h3>
                                <ActionBtn onClick={loadData}>Refresh</ActionBtn>
                            </CardHeader>

                            {isLoading ? (
                                <Spinner />
                            ) : sessions.length === 0 ? (
                                <EmptyState>
                                    <h4>No active sessions</h4>
                                </EmptyState>
                            ) : (
                                <Table>
                                    <thead>
                                        <tr>
                                            <Th>User</Th>
                                            <Th>Issued</Th>
                                            <Th>Expires</Th>
                                            <Th>Last Seen</Th>
                                            <Th>IP Address</Th>
                                            <Th>Action</Th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {sessions.map((s) => (
                                            <tr key={s.session_id}>
                                                <Td>{s.user_email}</Td>
                                                <Td>{formatDate(s.issued_at)}</Td>
                                                <Td>{formatDate(s.expires_at)}</Td>
                                                <Td>{formatDate(s.last_seen)}</Td>
                                                <Td>{s.ip_address || '-'}</Td>
                                                <Td>
                                                    <ActionBtn danger onClick={() => handleRevokeSession(s.session_id)}>
                                                        Revoke
                                                    </ActionBtn>
                                                </Td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </Table>
                            )}
                        </Card>
                    </>
                )}
            </MainContent>

            {selectedLog && (
                <ModalOverlay onClick={() => setSelectedLog(null)}>
                    <ModalContent onClick={e => e.stopPropagation()}>
                        <ModalHeader>
                            <h3>Audit Log Details</h3>
                            <CloseBtn onClick={() => setSelectedLog(null)}>
                                <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </CloseBtn>
                        </ModalHeader>
                        <ModalBody>
                            <DetailRow>
                                <label>Event ID</label>
                                <div>{selectedLog.event_id}</div>
                            </DetailRow>
                            <DetailRow>
                                <label>Timestamp</label>
                                <div>{formatDate(selectedLog.timestamp)}</div>
                            </DetailRow>
                            <DetailRow>
                                <label>User</label>
                                <div>{selectedLog.user_email || selectedLog.user_id}</div>
                            </DetailRow>
                            <DetailRow>
                                <label>Action</label>
                                <div>{selectedLog.action}</div>
                            </DetailRow>
                            <DetailRow>
                                <label>Details</label>
                                <JsonPre>
                                    {JSON.stringify(selectedLog.details, null, 2)}
                                </JsonPre>
                            </DetailRow>
                        </ModalBody>
                        <ModalFooter>
                            <ActionBtn onClick={() => setSelectedLog(null)}>Close</ActionBtn>
                        </ModalFooter>
                    </ModalContent>
                </ModalOverlay>
            )}
        </DashboardContainer>
    );
}
