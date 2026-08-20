import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from '@/components/ui/sonner';
import '@/App.css';

import { AuthProvider } from '@/contexts/AuthContext';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { UILayoutProvider } from '@/contexts/UILayoutContext';
import { AIPanelProvider } from '@/contexts/AIPanelContext';
import { MentorProvider } from '@/contexts/MentorContext';
import { ProtectedRoute, PublicOnlyRoute } from '@/components/ProtectedRoute';
import { AppShell } from '@/components/layout/AppShell';

import RootRedirect from '@/pages/RootRedirect';
import Login from '@/pages/auth/Login';
import Register from '@/pages/auth/Register';
import ForgotPassword from '@/pages/auth/ForgotPassword';
import ResetPassword from '@/pages/auth/ResetPassword';
import MissionInit from '@/pages/onboarding/MissionInit';
import MissionControl from '@/pages/dashboard/MissionControl';
import Assessment from '@/pages/assessment/Assessment';
import CodingArena from '@/pages/coding/CodingArena';
import SystemDesign from '@/pages/system-design/SystemDesign';
import KnowledgeBase from '@/pages/knowledge/KnowledgeBase';
import DeepTopicPage from '@/pages/knowledge/DeepTopicPage';
import AIMentor from '@/pages/ai-mentor/AIMentor';
import CommandAnalytics from '@/pages/analytics/CommandAnalytics';
import NotificationsPage from '@/pages/notifications/NotificationsPage';
import Settings from '@/pages/settings/Settings';
import Profile from '@/pages/profile/Profile';
import { useTheme } from '@/contexts/ThemeContext';

function ThemedToaster() {
  const { resolvedTheme } = useTheme();
  return <Toaster theme={resolvedTheme} richColors position="bottom-right" />;
}

function App() {
  return (
    <div className="App">
      <ThemeProvider>
        <BrowserRouter>
          <AuthProvider>
            <UILayoutProvider>
              <AIPanelProvider>
                <MentorProvider>
                  <Routes>
                    {/* Public */}
                    <Route path="/login" element={<PublicOnlyRoute><Login /></PublicOnlyRoute>} />
                    <Route path="/register" element={<PublicOnlyRoute><Register /></PublicOnlyRoute>} />
                    <Route path="/forgot-password" element={<PublicOnlyRoute><ForgotPassword /></PublicOnlyRoute>} />
                    <Route path="/reset-password" element={<ResetPassword />} />

                    {/* Onboarding (auth required, but no onboarding requirement) */}
                    <Route
                      path="/onboarding"
                      element={
                        <ProtectedRoute requireOnboarding={false}>
                          <MissionInit />
                        </ProtectedRoute>
                      }
                    />

                    {/* App shell (auth + onboarding required) */}
                    <Route
                      path="/app"
                      element={
                        <ProtectedRoute>
                          <AppShell />
                        </ProtectedRoute>
                      }
                    >
                      <Route path="mission-control" element={<MissionControl />} />
                      <Route path="assessment/:missionId" element={<Assessment />} />
                      <Route path="coding-arena" element={<CodingArena />} />
                      <Route path="system-design" element={<SystemDesign />} />
                      <Route path="knowledge-base" element={<KnowledgeBase />} />
                      <Route path="knowledge-base/nodes/:nodeId" element={<DeepTopicPage />} />
                      <Route path="ai-mentor" element={<AIMentor />} />
                      <Route path="analytics" element={<CommandAnalytics />} />
                      <Route path="notifications" element={<NotificationsPage />} />
                      <Route path="settings" element={<Settings />} />
                      <Route path="profile" element={<Profile />} />
                    </Route>

                    {/* Root */}
                    <Route path="/" element={<RootRedirect />} />
                    <Route path="*" element={<RootRedirect />} />
                  </Routes>
                </MentorProvider>
              </AIPanelProvider>
            </UILayoutProvider>
          </AuthProvider>
          <ThemedToaster />
        </BrowserRouter>
      </ThemeProvider>
    </div>
  );
}

export default App;
