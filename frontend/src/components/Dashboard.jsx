import React, { useState, useEffect } from 'react';
import styled, { keyframes } from 'styled-components';
import { logout, clearAuth } from '../api/auth';
import { submitQuery, getExampleQueries, downloadPdfReport } from '../api/agents';
import ResultsView from './ResultsView';

/**
 * BioMind Nexus Dashboard
 * Premium research dashboard matching LoginPage design theme.
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

const pulse = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`;

// ============================================
// Layout Styled Components
// ============================================

const DashboardContainer = styled.div`
  display: flex;
  min-height: 100vh;
  background-color: #f1f5f9;
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
  position: relative;

  /* Grid background */
  background-image: 
    linear-gradient(rgba(71, 85, 105, 0.08) 1px, transparent 1px),
    linear-gradient(90deg, rgba(71, 85, 105, 0.08) 1px, transparent 1px);
  background-size: 32px 32px;

  /* Ambient orbs */
  &::before {
    content: '';
    position: fixed;
    top: -10%;
    right: -5%;
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(37, 99, 235, 0.08) 0%, transparent 70%);
    border-radius: 50%;
    filter: blur(80px);
    animation: ${float} 12s ease-in-out infinite;
    z-index: 0;
    pointer-events: none;
  }
`;

const Sidebar = styled.aside`
  width: 280px;
  background: #0f172a;
  color: white;
  display: flex;
  flex-direction: column;
  padding: 2rem 0;
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  z-index: 100;

  @media (max-width: 1024px) {
    width: 80px;
  }
`;

const SidebarBrand = styled.div`
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 1.5rem;
  margin-bottom: 2.5rem;

  svg {
    width: 32px;
    height: 32px;
    flex-shrink: 0;
  }

  span {
    font-weight: 800;
    font-size: 1.15rem;
    letter-spacing: -0.02em;

    @media (max-width: 1024px) {
      display: none;
    }
  }
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
  background: ${props => props.active ? 'rgba(59, 130, 246, 0.15)' : 'transparent'};
  border: none;
  border-radius: 12px;
  color: ${props => props.active ? '#60a5fa' : 'rgba(255, 255, 255, 0.7)'};
  font-size: 0.9rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s;
  text-align: left;

  &:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  svg {
    width: 20px;
    height: 20px;
    flex-shrink: 0;
  }

  span {
    @media (max-width: 1024px) {
      display: none;
    }
  }
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
    background: linear-gradient(135deg, #2563eb, #1d4ed8);
    border-radius: 10px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-weight: 700;
    font-size: 0.95rem;
  }

  .details {
    flex: 1;
    overflow: hidden;

    @media (max-width: 1024px) {
      display: none;
    }

    .name {
      font-weight: 600;
      font-size: 0.9rem;
      color: white;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .role {
      font-size: 0.75rem;
      color: rgba(255, 255, 255, 0.5);
      text-transform: capitalize;
    }
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

  &:hover {
    background: rgba(239, 68, 68, 0.15);
    color: #ef4444;
  }

  svg {
    width: 18px;
    height: 18px;
  }
`;

const MainContent = styled.main`
  flex: 1;
  margin-left: 280px;
  padding: 2rem;
  position: relative;
  z-index: 1;

  @media (max-width: 1024px) {
    margin-left: 80px;
  }
`;

const PageHeader = styled.div`
  margin-bottom: 2rem;
  animation: ${fadeIn} 0.5s ease-out;

  h1 {
    font-size: 2rem;
    font-weight: 800;
    color: #0f172a;
    letter-spacing: -0.04em;
    margin: 0 0 0.5rem 0;
  }

  p {
    color: #64748b;
    font-size: 1rem;
    margin: 0;
  }
`;

// ============================================
// Query Section
// ============================================

const QueryCard = styled.div`
  background: white;
  border-radius: 20px;
  padding: 2rem;
  box-shadow: 0 4px 20px -4px rgba(15, 23, 42, 0.08);
  margin-bottom: 2rem;
  animation: ${fadeIn} 0.5s ease-out 0.1s backwards;
`;

const QueryInput = styled.textarea`
  width: 100%;
  min-height: 120px;
  padding: 1.25rem;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  font-size: 1rem;
  color: #0f172a;
  resize: vertical;
  font-family: inherit;
  transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);

  &::placeholder {
    color: #94a3b8;
  }

  &:hover {
    background: white;
    border-color: #cbd5e1;
  }

  &:focus {
    outline: none;
    background: white;
    border-color: #3b82f6;
    transform: translateY(-2px);
    box-shadow: 0 10px 20px -5px rgba(59, 130, 246, 0.15), 0 0 0 4px rgba(59, 130, 246, 0.1);
  }
`;

const QueryActions = styled.div`
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 1.25rem;
  gap: 1rem;
`;

const ExampleQueries = styled.div`
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  flex: 1;
`;

const ExampleChip = styled.button`
  padding: 0.5rem 0.875rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 99px;
  font-size: 0.8rem;
  color: #475569;
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    background: #e2e8f0;
    border-color: #cbd5e1;
  }
`;

const SubmitButton = styled.button`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.75rem;
  background: linear-gradient(135deg, #1e40af 0%, #2563eb 100%);
  color: white;
  border: none;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);

  &:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: 0 10px 15px -3px rgba(37, 99, 235, 0.3);
  }

  &:disabled {
    opacity: 0.7;
    cursor: not-allowed;
  }

  svg {
    width: 18px;
    height: 18px;
  }
`;

const Spinner = styled.div`
  width: 18px;
  height: 18px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-radius: 50%;
  border-top-color: white;
  animation: ${spin} 0.8s linear infinite;
`;

// ============================================
// Results Section
// ============================================

const ResultsSection = styled.div`
  animation: ${fadeIn} 0.5s ease-out 0.2s backwards;
`;

const SectionTitle = styled.h2`
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 1rem 0;
  display: flex;
  align-items: center;
  gap: 0.5rem;
`;

const ResultsGrid = styled.div`
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.25rem;
`;

const CandidateCard = styled.div`
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  box-shadow: 0 2px 12px -2px rgba(15, 23, 42, 0.06);
  border: 1px solid #e2e8f0;
  transition: all 0.2s;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 20px -4px rgba(15, 23, 42, 0.12);
    border-color: #cbd5e1;
  }
`;

const CandidateHeader = styled.div`
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 1rem;
`;

const DrugName = styled.h3`
  font-size: 1.1rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
`;

const DiseaseBadge = styled.span`
  font-size: 0.75rem;
  color: #64748b;
  background: #f1f5f9;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
`;

const ConfidenceScore = styled.div`
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: ${props => props.high ? '#059669' : props.medium ? '#d97706' : '#dc2626'};

  .score {
    font-size: 1.25rem;
  }
`;

const Hypothesis = styled.p`
  font-size: 0.9rem;
  color: #475569;
  line-height: 1.6;
  margin: 0 0 1rem 0;
`;

const EvidenceCount = styled.div`
  font-size: 0.8rem;
  color: #64748b;
  display: flex;
  align-items: center;
  gap: 0.375rem;
`;

// ============================================
// Empty State
// ============================================

const EmptyState = styled.div`
  text-align: center;
  padding: 4rem 2rem;
  color: #64748b;
  animation: ${fadeIn} 0.5s ease-out;

  svg {
    width: 64px;
    height: 64px;
    margin-bottom: 1.5rem;
    opacity: 0.5;
  }

  h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #334155;
    margin: 0 0 0.5rem 0;
  }

  p {
    font-size: 0.95rem;
    margin: 0;
  }
`;

// ============================================
// Loading State
// ============================================

const LoadingOverlay = styled.div`
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 4rem 2rem;
  text-align: center;

  .loader {
    width: 48px;
    height: 48px;
    border: 3px solid #e2e8f0;
    border-top-color: #2563eb;
    border-radius: 50%;
    animation: ${spin} 0.8s linear infinite;
    margin-bottom: 1.5rem;
  }

  h3 {
    font-size: 1.1rem;
    font-weight: 600;
    color: #0f172a;
    margin: 0 0 0.5rem 0;
  }

  p {
    font-size: 0.9rem;
    color: #64748b;
    margin: 0;
    animation: ${pulse} 2s ease-in-out infinite;
  }
`;

// ============================================
// Component
// ============================================

export default function Dashboard({ user, onLogout }) {
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState(null);
  const [examples, setExamples] = useState([]);
  const [activeView, setActiveView] = useState('query');
  const [isDownloadingPdf, setIsDownloadingPdf] = useState(false);

  // Load example queries on mount
  useEffect(() => {
    async function loadExamples() {
      try {
        const data = await getExampleQueries();
        setExamples(data.examples || []);
      } catch (err) {
        console.log('Examples not available');
      }
    }
    loadExamples();
  }, []);

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

  const handleSubmitQuery = async () => {
    if (!query.trim()) return;

    setIsLoading(true);
    setResults(null);

    try {
      const response = await submitQuery(query);
      setResults(response);
    } catch (err) {
      console.error('Query failed:', err);
      // Show error state
    } finally {
      setIsLoading(false);
    }
  };

  const getInitials = (email) => {
    return email ? email.substring(0, 2).toUpperCase() : 'U';
  };

  const getConfidenceLevel = (score) => {
    if (score >= 0.7) return 'high';
    if (score >= 0.4) return 'medium';
    return 'low';
  };

  const handleDownloadPdf = async () => {
    if (!results?.query_id) return;
    setIsDownloadingPdf(true);
    try {
      const blob = await downloadPdfReport(results.query_id);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `biomind_report_${results.query_id}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      a.remove();
    } catch (err) {
      console.error('PDF download failed:', err);
    } finally {
      setIsDownloadingPdf(false);
    }
  };

  return (
    <DashboardContainer>
      {/* Sidebar Navigation */}
      <Sidebar>
        <SidebarBrand>
          <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z" stroke="white" strokeWidth="2.5" />
            <path d="M8 12L11 15L16 9" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          <span>BioMind Nexus</span>
        </SidebarBrand>

        <NavSection>
          <NavItem active={activeView === 'query'} onClick={() => setActiveView('query')}>
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
            <span>Query Analysis</span>
          </NavItem>
          <NavItem active={activeView === 'graph'} onClick={() => setActiveView('graph')}>
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
            <span>Knowledge Graph</span>
          </NavItem>
          <NavItem active={activeView === 'history'} onClick={() => setActiveView('history')}>
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <span>Query History</span>
          </NavItem>
          <NavItem active={activeView === 'reports'} onClick={() => setActiveView('reports')}>
            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span>Dossiers</span>
          </NavItem>
        </NavSection>

        <SidebarFooter>
          <UserInfo>
            <div className="avatar">{getInitials(user?.email)}</div>
            <div className="details">
              <div className="name">{user?.email || 'Researcher'}</div>
              <div className="role">{user?.role || 'researcher'}</div>
            </div>
            <LogoutBtn onClick={handleLogout} title="Sign out">
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
              </svg>
            </LogoutBtn>
          </UserInfo>
        </SidebarFooter>
      </Sidebar>

      {/* Main Content */}
      <MainContent>
        {/* Query Analysis View */}
        {activeView === 'query' && (
          <>
            <PageHeader>
              <h1>Drug Repurposing Analysis</h1>
              <p>Ask questions about potential drug repurposing opportunities</p>
            </PageHeader>

            {/* Query Input Card */}
            <QueryCard>
              <QueryInput
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Enter your drug repurposing question... e.g., 'Can metformin be repurposed for breast cancer treatment?'"
                disabled={isLoading}
              />
              <QueryActions>
                <ExampleQueries>
                  {examples.slice(0, 3).map((ex, i) => (
                    <ExampleChip key={i} onClick={() => setQuery(ex.query)}>
                      {ex.query.length > 50 ? ex.query.substring(0, 50) + '...' : ex.query}
                    </ExampleChip>
                  ))}
                </ExampleQueries>
                <SubmitButton onClick={handleSubmitQuery} disabled={isLoading || !query.trim()}>
                  {isLoading ? (
                    <Spinner />
                  ) : (
                    <>
                      <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                      </svg>
                      Analyze
                    </>
                  )}
                </SubmitButton>
              </QueryActions>
            </QueryCard>

            {/* Loading State */}
            {isLoading && (
              <LoadingOverlay>
                <div className="loader" />
                <h3>Analyzing your query...</h3>
                <p>Running entity extraction, literature search, and reasoning agents</p>
              </LoadingOverlay>
            )}

            {/* Results - Three Panel View */}
            {!isLoading && results && (
              <ResultsView
                queryId={results.query_id}
                results={results}
                onDownloadPdf={handleDownloadPdf}
                isDownloading={isDownloadingPdf}
              />
            )}

            {/* Empty State */}
            {!isLoading && !results && (
              <EmptyState>
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                </svg>
                <h3>Ready to explore drug repurposing</h3>
                <p>Enter a query above to discover potential therapeutic opportunities</p>
              </EmptyState>
            )}
          </>
        )}

        {/* Knowledge Graph View */}
        {activeView === 'graph' && (
          <>
            <PageHeader>
              <h1>Knowledge Graph Explorer</h1>
              <p>Explore the biomedical knowledge graph of drugs, diseases, and pathways</p>
            </PageHeader>
            <EmptyState>
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <h3>Knowledge Graph</h3>
              <p>Run a query to see the relevant subgraph visualization</p>
              <SubmitButton onClick={() => setActiveView('query')} style={{ marginTop: '1rem' }}>
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Start Analysis
              </SubmitButton>
            </EmptyState>
          </>
        )}

        {/* Query History View */}
        {activeView === 'history' && (
          <>
            <PageHeader>
              <h1>Query History</h1>
              <p>View your past drug repurposing analyses</p>
            </PageHeader>
            <EmptyState>
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <h3>No History Yet</h3>
              <p>Your completed queries will appear here for quick reference</p>
              <SubmitButton onClick={() => setActiveView('query')} style={{ marginTop: '1rem' }}>
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                New Query
              </SubmitButton>
            </EmptyState>
          </>
        )}

        {/* Reports/Dossiers View */}
        {activeView === 'reports' && (
          <>
            <PageHeader>
              <h1>Research Dossiers</h1>
              <p>Download and manage your generated PDF reports</p>
            </PageHeader>
            <EmptyState>
              <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <h3>No Reports Yet</h3>
              <p>Generate a report by running a query and clicking "Download PDF"</p>
              <SubmitButton onClick={() => setActiveView('query')} style={{ marginTop: '1rem' }}>
                <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Create Report
              </SubmitButton>
            </EmptyState>
          </>
        )}
      </MainContent>
    </DashboardContainer>
  );
}
