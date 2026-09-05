import { useEffect, useState } from 'react';
import { toast } from 'sonner';
import {
  Tabs, TabsContent, TabsList, TabsTrigger,
} from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { GlassCard } from '@/components/common/GlassCard';
import { userService } from '@/services/auth.service';
import { useAuth } from '@/contexts/AuthContext';
import { TARGET_COMPANIES } from '@/config/companies';
import { formatApiError } from '@/utils/formatApiError';
import { SETTINGS } from '@/constants/testIds';
import { Loader2, Save, Sun, Moon, Monitor } from 'lucide-react';
import { cn } from '@/lib/utils';
import { useTheme } from '@/contexts/ThemeContext';

export default function Settings() {
  const { user, refresh } = useAuth();
  const { theme: activeTheme, setTheme } = useTheme();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [settings, setSettings] = useState(null);
  const [onboarding, setOnboarding] = useState(null);
  const [name, setName] = useState('');

  useEffect(() => {
    (async () => {
      try {
        const [s, o] = await Promise.all([
          userService.getSettings(),
          userService.getOnboarding(),
        ]);
        setSettings(s);
        setOnboarding(o);
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  useEffect(() => { if (user) setName(user.name); }, [user]);

  if (loading || !settings) {
    return <div className="py-20 text-center text-muted-foreground">Loading…</div>;
  }

  const patch = (partial) => setSettings((s) => ({ ...s, ...partial }));
  const patchNotif = (partial) => setSettings((s) => ({ ...s, notification_prefs: { ...s.notification_prefs, ...partial } }));

  const save = async () => {
    setSaving(true);
    try {
      if (name && name !== user.name) {
        await userService.updateProfile({ name });
        await refresh();
      }
      const updated = await userService.updateSettings({
        theme: settings.theme,
        notification_prefs: settings.notification_prefs,
      });
      setSettings(updated);
      toast.success('Settings saved.');
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid={SETTINGS.root}>
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="overline mb-2">Settings</div>
          <h1 className="font-display text-3xl sm:text-4xl font-semibold tracking-tight">
            Workspace preferences
          </h1>
          <p className="mt-2 text-sm text-muted-foreground max-w-2xl">
            Tune your workspace, target companies, and notification preferences.
          </p>
        </div>
        <Button
          onClick={save}
          disabled={saving}
          data-testid={SETTINGS.saveButton}
          className="h-10 bg-primary hover:bg-primary/90 btn-primary-glow"
        >
          {saving ? <><Loader2 className="h-4 w-4 mr-2 animate-spin" />Saving…</> : <><Save className="h-4 w-4 mr-2" />Save changes</>}
        </Button>
      </div>

      <Tabs defaultValue="profile" className="w-full">
        <TabsList className="bg-[hsl(var(--surface))]/60 border border-white/[0.06] rounded-xl p-1 flex w-full flex-wrap h-auto">
          <TabsTrigger value="profile" data-testid={SETTINGS.tabProfile} className="data-[state=active]:bg-primary/15 data-[state=active]:text-foreground rounded-lg px-4 py-2">Profile</TabsTrigger>
          <TabsTrigger value="theme" data-testid={SETTINGS.tabTheme} className="data-[state=active]:bg-primary/15 data-[state=active]:text-foreground rounded-lg px-4 py-2">Theme</TabsTrigger>
          <TabsTrigger value="study" data-testid={SETTINGS.tabStudy} className="data-[state=active]:bg-primary/15 data-[state=active]:text-foreground rounded-lg px-4 py-2">Study hours</TabsTrigger>
          <TabsTrigger value="companies" data-testid={SETTINGS.tabCompanies} className="data-[state=active]:bg-primary/15 data-[state=active]:text-foreground rounded-lg px-4 py-2">Target Companies</TabsTrigger>
          <TabsTrigger value="notifications" data-testid={SETTINGS.tabNotifications} className="data-[state=active]:bg-primary/15 data-[state=active]:text-foreground rounded-lg px-4 py-2">Notifications</TabsTrigger>
        </TabsList>

        {/* Profile */}
        <TabsContent value="profile" className="mt-6">
          <GlassCard className="p-6 space-y-5 max-w-2xl">
            <div>
              <Label className="mb-1.5 block text-xs font-mono uppercase tracking-wider text-muted-foreground">Full name</Label>
              <Input value={name} onChange={(e) => setName(e.target.value)} className="bg-white/[0.03] border-white/10" />
            </div>
            <div>
              <Label className="mb-1.5 block text-xs font-mono uppercase tracking-wider text-muted-foreground">Email</Label>
              <Input value={user.email} disabled className="bg-white/[0.02] border-white/10 opacity-70" />
              <p className="mt-1.5 text-xs text-muted-foreground">Email is used as your unique identifier — cannot be edited yet.</p>
            </div>
          </GlassCard>
        </TabsContent>

        {/* Theme */}
        <TabsContent value="theme" className="mt-6">
          <GlassCard className="p-6 max-w-2xl">
            <p className="text-sm text-muted-foreground mb-4">
              Choose how PrepOS looks. System matches your operating system preference and updates automatically.
            </p>
            <div className="grid grid-cols-3 gap-3">
              {[
                { id: 'light',  label: 'Light',  hint: 'Bright · calm',      icon: Sun },
                { id: 'dark',   label: 'Dark',   hint: 'Default · premium', icon: Moon },
                { id: 'system', label: 'System', hint: 'Follows OS',        icon: Monitor },
              ].map((t) => {
                const active = activeTheme === t.id;
                const Icon = t.icon;
                return (
                  <button
                    key={t.id}
                    onClick={() => { setTheme(t.id); patch({ theme: t.id }); }}
                    data-testid={`settings-theme-${t.id}`}
                    className={cn(
                      'relative rounded-xl border p-4 text-left transition-all',
                      active
                        ? 'border-primary/50 bg-primary/10 shadow-[0_0_0_1px_hsl(var(--primary)/0.3)]'
                        : 'hairline bg-foreground/[0.02] hover:bg-foreground/[0.04]',
                    )}
                  >
                    <Icon className={cn('h-4 w-4 mb-2', active ? 'text-primary' : 'text-muted-foreground')} />
                    <div className="capitalize font-medium">{t.label}</div>
                    <div className="text-xs text-muted-foreground mt-0.5">{t.hint}</div>
                  </button>
                );
              })}
            </div>
          </GlassCard>
        </TabsContent>

        {/* Study hours */}
        <TabsContent value="study" className="mt-6">
          <GlassCard className="p-6 max-w-2xl">
            <div className="overline mb-2">Current baseline (from onboarding)</div>
            <div className="flex items-baseline gap-2 mb-6">
              <span className="font-display text-4xl font-semibold">
                {onboarding?.daily_study_hours ?? '—'}
              </span>
              <span className="text-sm text-muted-foreground">hours / day</span>
            </div>
            <p className="text-sm text-muted-foreground">
              Editing your daily study budget lives with the Mission Engine (Phase 2), so it can rebalance your plan.
            </p>
          </GlassCard>
        </TabsContent>

        {/* Companies */}
        <TabsContent value="companies" className="mt-6">
          <GlassCard className="p-6">
            <div className="overline mb-3">Your targets</div>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-3">
              {TARGET_COMPANIES.map((c) => {
                const active = onboarding?.target_companies?.includes(c.id);
                return (
                  <div
                    key={c.id}
                    className={cn(
                      'rounded-xl border px-3 py-3 flex items-center gap-2.5',
                      active ? 'border-primary/40 bg-primary/10' : 'border-white/[0.06] bg-white/[0.02] opacity-70',
                    )}
                  >
                    <span
                      className="h-7 w-7 rounded-md border border-white/10 flex items-center justify-center font-mono text-xs"
                      style={{ background: `${c.accent}20`, color: c.accent === '#000000' ? '#fff' : c.accent }}
                    >
                      {c.name[0]}
                    </span>
                    <span className="text-sm">{c.name}</span>
                  </div>
                );
              })}
            </div>
            <p className="mt-4 text-xs text-muted-foreground">
              Editing targets rebalances your mission plan and ships with the Mission Engine.
            </p>
          </GlassCard>
        </TabsContent>

        {/* Notifications */}
        <TabsContent value="notifications" className="mt-6">
          <GlassCard className="p-6 space-y-4 max-w-2xl">
            {[
              { key: 'email_daily_digest',       label: 'Daily digest', hint: 'Email summary of your day, mission and next steps.' },
              { key: 'email_weekly_report',      label: 'Weekly report', hint: 'End-of-week analytics and retention checkpoints.' },
              { key: 'push_streak_reminders',    label: 'Streak reminders', hint: 'Nudge me when I might lose my streak.' },
              { key: 'push_upcoming_revisions',  label: 'Upcoming revisions', hint: 'Alerts when spaced-repetition items are due.' },
              { key: 'push_mission_updates',     label: 'Mission updates', hint: 'When missions are generated or rebalanced.' },
            ].map((row) => (
              <div key={row.key} className="flex items-start gap-4 rounded-lg border border-white/[0.06] bg-white/[0.02] p-4">
                <div className="flex-1">
                  <p className="text-sm font-medium">{row.label}</p>
                  <p className="text-xs text-muted-foreground">{row.hint}</p>
                </div>
                <Switch
                  checked={settings.notification_prefs[row.key]}
                  onCheckedChange={(v) => patchNotif({ [row.key]: v })}
                />
              </div>
            ))}
          </GlassCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
