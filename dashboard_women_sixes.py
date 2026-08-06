import streamlit as st
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import plotly.graph_objects as go
import os
import shutil
import io

# ==========================================
# 🌟 終極防破圖系統：暴力清快取 + 絕對路徑字體
# ==========================================
cache_dir = mpl.get_cachedir()
if os.path.exists(cache_dir):
    shutil.rmtree(cache_dir, ignore_errors=True)

current_dir = os.path.dirname(os.path.abspath(__file__))
font_path = os.path.join(current_dir, "NotoSansTC-Regular.ttf")

if os.path.exists(font_path):
    fm.fontManager.addfont(font_path)
    prop = fm.FontProperties(fname=font_path)
    plt.rcParams['font.family'] = prop.get_name()
    plt.rcParams['font.sans-serif'] = [prop.get_name(), 'sans-serif']
else:
    st.warning("⚠️ 找不到 NotoSansTC-Regular.ttf 字體檔！請確認已上傳至 GitHub。目前暫時使用系統備用字體。")
    plt.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'Arial Unicode MS', 'sans-serif']

plt.rcParams['axes.unicode_minus'] = False

# ==========================================
# 🌟 女子六人制 (Women's Sixes) 基準數據庫
# ==========================================
WOMEN_SIXES_TOP_SPEED = 5.5      
WOMEN_SIXES_AVG_SPEED = 74.0      
WOMEN_SIXES_SPRINT_DIST = 3.6    # 對標 Zone 4 Distance

WOMEN_SIXES_BASELINES = {
    'World Class Sixes (Women)': {
        'dist': 2412, 
        'avg_spd': WOMEN_SIXES_AVG_SPEED, 
        'top_spd': WOMEN_SIXES_TOP_SPEED, 
        'sprint_dist': WOMEN_SIXES_SPRINT_DIST
    }
}
default_baseline_name = list(WOMEN_SIXES_BASELINES.keys())[0]
default_baseline_data = WOMEN_SIXES_BASELINES[default_baseline_name]

# ==========================================
# 🌟 輔助函數：智慧階梯算法 & 圖片下載轉換器
# ==========================================
def get_dist_ymax(max_val):
    if pd.isna(max_val) or max_val <= 0: return 2000
    if max_val <= 2000: return 2000
    elif max_val <= 4000: return 4000
    elif max_val <= 6000: return 6000
    elif max_val <= 8000: return 8000
    elif max_val <= 10000: return 10000
    else: return (int(max_val) // 10000 + 1) * 10000

def get_img_buffer(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=300) 
    buf.seek(0)
    return buf

st.set_page_config(page_title="女網六人制 GPS 數據儀表板", layout="wide")

@st.cache_data
def load_data(file_path):
    if os.path.exists(file_path):
        return pd.read_csv(file_path)
    return None

# 讀取新的六人制資料表 (您可以根據實際檔名修改)
df = load_data('Cleaned_GPS_Data_Women.csv')

if df is None:
    st.error("❌ 找不到資料！請確認 Cleaned_GPS_Data_Women.csv 是否存在。")
else:
    # 🌟 關鍵轉換：將 Zone 4 Distance 轉換為 Sprint Distance
    if 'Zone 4 Distance (m)' in df.columns: 
        df.rename(columns={'Zone 4 Distance (m)': 'Sprint Distance (m)'}, inplace=True)
    
    df = df[~df['Player'].astype(str).str.contains('#')]
    df['Date'] = df['Session'].astype(str).apply(lambda x: x.split()[0])
    
    def get_month(date_str):
        try:
            return int(str(date_str).split('/')[0])
        except:
            return 0
    df['Month'] = df['Date'].apply(get_month)

    def generate_agg_df(subset_df, period_name):
        daily_totals = subset_df[subset_df['Session'].astype(str).str.contains('Total|total', case=False, na=False)]
        if daily_totals.empty:
            daily_totals = subset_df
            
        agg_funcs = {
            'Total Distance (m)': 'sum',
            'Avg Speed (m/min)': 'mean',
            'Top Speed (m/s)': 'max',
            'Sprint Distance (m)': 'sum' # 🌟 Sprint 是距離，聚合時使用加總
        }
        if 'RPE' in daily_totals.columns: agg_funcs['RPE'] = 'mean'
        if 'Position' in daily_totals.columns: agg_funcs['Position'] = 'first'
        
        agg = daily_totals.groupby('Player').agg(agg_funcs).reset_index()
        
        if 'RPE' in agg.columns:
            agg['RPE'] = agg['RPE'].round(1)
            
        agg['Date'] = period_name
        agg['Session'] = period_name + ' Total'
        return agg

    agg_dfs = []
    for m in df['Month'].unique():
        if m > 0:
            m_df = df[df['Month'] == m]
            if not m_df.empty:
                agg_dfs.append(generate_agg_df(m_df, f'{m}月份'))
                
    q1_df = df[df['Month'].isin([1, 2, 3])]
    if not q1_df.empty:
        agg_dfs.append(generate_agg_df(q1_df, 'Q1 (1-3月)'))

    if 'custom_periods' not in st.session_state:
        st.session_state['custom_periods'] = {}

    st.sidebar.title("🥍 女網六人制 戰情室導覽")
    st.sidebar.markdown("### 🔄 建立專屬盃賽/週期")
    raw_dates = [d for d in df['Date'].unique() if '/' in str(d)]
    
    with st.sidebar.expander("🛠️ 點此展開盃賽融合器"):
        new_cycle_name = st.text_input("週期名稱 (例: 世界運動會):")
        selected_cycle_dates = st.multiselect("選擇要融合的日期:", raw_dates)
        if st.button("➕ 建立專屬週期資料"):
            if new_cycle_name and selected_cycle_dates:
                st.session_state['custom_periods'][new_cycle_name] = selected_cycle_dates
                st.rerun()

    for c_name, c_dates in st.session_state['custom_periods'].items():
        c_df = df[df['Date'].isin(c_dates)]
        if not c_df.empty:
            agg_dfs.append(generate_agg_df(c_df, c_name))

    if agg_dfs:
        df = pd.concat([df] + agg_dfs, ignore_index=True)
        
    custom_and_auto_names = list(st.session_state['custom_periods'].keys()) + ['Q1 (1-3月)'] + [f'{m}月份' for m in df['Month'].unique() if m > 0]

    st.sidebar.markdown("---") 
    page_mode = st.sidebar.radio(
        "📌 選擇分析模式：", 
        ["📊 團隊總覽 (Team Dashboard)", "👤 個人報告 (Player Profile)"]
    )
    st.sidebar.markdown("---") 

    # ==========================================
    # 模式一：團隊總覽 (Team Dashboard)
    # ==========================================
    if page_mode == "📊 團隊總覽 (Team Dashboard)":
        st.title("🥍 女網六人制 GPS 戰情室 - 團隊總覽")
        st.sidebar.header("⚙️ 團隊設定面板")
        
        available_dates = df['Date'].dropna().unique().tolist()
        for name in reversed(custom_and_auto_names):
            if name in available_dates:
                available_dates.remove(name)
                available_dates.insert(0, name)
                
        selected_date = st.sidebar.selectbox("📅 第一步：選擇日期或週期", available_dates, key='team_date')
        sessions_for_date = df[df['Date'] == selected_date]['Session'].unique().tolist()
        selected_session = st.sidebar.selectbox("⏱️ 第二步：選擇時段", sessions_for_date, key='team_session')
        
        st.write("---")
        df_filtered = df[df['Session'] == selected_session]
        
        if not df_filtered.empty:
            # 🌟 聚合加入 Sprint Distance
            agg_dict = {'Total Distance (m)': 'max', 'Avg Speed (m/min)': 'mean', 'Top Speed (m/s)': 'max', 'Sprint Distance (m)': 'max'}
            if 'RPE' in df_filtered.columns: agg_dict['RPE'] = 'max'
            if 'Position' in df_filtered.columns: agg_dict['Position'] = 'first'
            
            df_plot = df_filtered.groupby('Player').agg(agg_dict).reset_index()

            st.subheader(f"1️⃣ {selected_session} 外部與內部負荷")
            fig1, ax1 = plt.subplots(figsize=(12, 3.5))
            bars1 = ax1.bar(df_plot['Player'], df_plot['Total Distance (m)'], color='#e06666', width=0.5)
            
            # 對標六人制數據
            ax1.axhline(y=default_baseline_data['dist'], color='gold', linestyle='-', linewidth=2, label=default_baseline_name)
            
            team_avg_dist = df_plot['Total Distance (m)'].mean()
            if pd.notna(team_avg_dist):
                ax1.axhline(y=team_avg_dist, color='blue', linestyle='--', label='Team Avg')
            
            for bar in bars1:
                yval = bar.get_height()
                if pd.notna(yval) and yval > 0:
                    ax1.text(bar.get_x() + bar.get_width()/2, yval/2 + 200, int(yval), ha='center', va='center', color='white', fontweight='bold', fontsize=12)
                    if 'RPE' in df_plot.columns:
                        rpe_val = df_plot.loc[df_plot['Total Distance (m)'] == yval, 'RPE'].values[0]
                        if pd.notna(rpe_val) and rpe_val > 0:
                            ax1.text(bar.get_x() + bar.get_width()/2, yval/2 - 200, f"RPE: {rpe_val}", ha='center', va='center', color='#ffd966', fontweight='bold', fontsize=11)
            
            ax1.margins(x=0.05)
            ax1.set_ylim(0, get_dist_ymax(df_plot['Total Distance (m)'].max()))
            ax1.legend()
            st.pyplot(fig1)
            st.download_button(label="📥 下載圖表 (外部與內部負荷)", data=get_img_buffer(fig1), file_name=f"Total_Distance_{selected_session}.png", mime="image/png")

            col1, col2 = st.columns(2)
            with col1:
                st.subheader("2️⃣ 平均速度表現 (vs. Sixes Benchmark)")
                spd_mode = st.radio("顯示模式：", ["📌 當前時段", "📅 多日比較 (最多5天)"], horizontal=True, key='spd_mode')
                
                if spd_mode == "📌 當前時段":
                    fig2, ax2 = plt.subplots(figsize=(6, 4))
                    bars2 = ax2.bar(df_plot['Player'], df_plot['Avg Speed (m/min)'], color='#c27ba0', width=0.5)
                    ax2.axhline(y=default_baseline_data['avg_spd'], color='gold', linestyle='-', linewidth=2, label=default_baseline_name)
                    
                    team_avg_spd = df_plot['Avg Speed (m/min)'].mean()
                    if pd.notna(team_avg_spd):
                        ax2.axhline(y=team_avg_spd, color='blue', linestyle='--', alpha=0.5, label='Team Avg')
                    
                    ax2.margins(x=0.1)
                    max_spd = df_plot['Avg Speed (m/min)'].max()
                    max_spd = max(max_spd, default_baseline_data['avg_spd']) if pd.notna(max_spd) else default_baseline_data['avg_spd']
                    y_max_spd = max(100, (int(max_spd) // 20 + 1) * 20)
                    ax2.set_ylim(0, y_max_spd)
                    ax2.legend(loc='lower right')
                    st.pyplot(fig2)
                    st.download_button(label="📥 下載圖表 (平均速度)", data=get_img_buffer(fig2), file_name=f"Avg_Speed_{selected_session}.png", mime="image/png")
                else:
                    valid_dates = [d for d in df['Date'].unique() if '/' in str(d) and d not in custom_and_auto_names]
                    default_d = selected_date if selected_date in valid_dates else valid_dates[-1] if valid_dates else None
                    selected_spd_dates = st.multiselect("選擇欲比較的日期 (最多5天)：", valid_dates, default=[default_d] if default_d else [], max_selections=5, key='spd_multi')
                    
                    if selected_spd_dates:
                        df_spd = df[(df['Date'].isin(selected_spd_dates)) & (df['Session'].astype(str).str.contains('Total|total', case=False, na=False))]
                        if not df_spd.empty:
                            players_spd = sorted(df_spd['Player'].unique())
                            fig2, ax2 = plt.subplots(figsize=(6, 4))
                            x = np.arange(len(players_spd))
                            width = 0.8 / len(selected_spd_dates)
                            colors_spd = ['#c27ba0', '#8e7cc3', '#6fa8dc', '#f6b26b', '#93c47d']
                            
                            ax2.axhline(y=default_baseline_data['avg_spd'], color='gold', linestyle='-', linewidth=2, label=default_baseline_name)
                            
                            for i, d_date in enumerate(selected_spd_dates):
                                d_data = df_spd[df_spd['Date'] == d_date]
                                y_vals = [d_data[d_data['Player'] == p]['Avg Speed (m/min)'].max() if not d_data[d_data['Player'] == p].empty else 0 for p in players_spd]
                                offset = i * width - (0.8/2) + (width/2)
                                ax2.bar(x + offset, y_vals, width, label=f"{d_date}", color=colors_spd[i%len(colors_spd)])
                            
                            ax2.set_xticks(x)
                            ax2.set_xticklabels(players_spd)
                            ax2.margins(x=0.05)
                            
                            max_spd = df_spd['Avg Speed (m/min)'].max()
                            max_spd = max(max_spd, default_baseline_data['avg_spd']) if pd.notna(max_spd) else default_baseline_data['avg_spd']
                            y_max_spd = max(100, (int(max_spd) // 20 + 1) * 20)
                            ax2.set_ylim(0, y_max_spd)
                            ax2.legend(loc='lower right', fontsize='small')
                            st.pyplot(fig2)
                            st.download_button(label="📥 下載圖表 (平均速度比較)", data=get_img_buffer(fig2), file_name="Avg_Speed_Compare.png", mime="image/png")
                        else:
                            st.info("💡 找不到所選日期的 Total 數據來進行比較。")
                    else:
                        st.info("💡 請至少選擇一個日期。")

            with col2:
                is_custom_or_auto = selected_date in custom_and_auto_names
                if is_custom_or_auto:
                    st.subheader(f"3️⃣ {selected_date} 每日負荷消長")
                    if selected_date in st.session_state['custom_periods']:
                        target_dates = st.session_state['custom_periods'][selected_date]
                    elif selected_date == 'Q1 (1-3月)':
                        target_dates = df[df['Month'].isin([1, 2, 3])]['Date'].unique().tolist()
                    elif '月份' in selected_date:
                        m = int(selected_date.replace('月份', ''))
                        target_dates = df[df['Month'] == m]['Date'].unique().tolist()
                    else:
                        target_dates = []
                        
                    target_dates = [d for d in target_dates if d not in custom_and_auto_names and '/' in str(d)]
                    df_q = df[(df['Date'].isin(target_dates)) & (df['Session'].astype(str).str.contains('Total|total', case=False, na=False))]
                    
                    if not df_q.empty:
                        daily_sessions = sorted(df_q['Date'].unique().tolist())
                        players = sorted(df_q['Player'].unique())
                        fig3_q, ax3_q = plt.subplots(figsize=(6, 4))
                        x = np.arange(len(players))
                        width = 0.8 / len(daily_sessions) if len(daily_sessions) > 0 else 0.8
                        colors = ['#6fa8dc', '#f6b26b', '#93c47d', '#ffd966', '#c27ba0', '#8e7cc3']
                        
                        for i, d_date in enumerate(daily_sessions):
                            d_data = df_q[df_q['Date'] == d_date]
                            y_vals = [d_data[d_data['Player'] == p]['Total Distance (m)'].max() if not d_data[d_data['Player'] == p].empty else 0 for p in players]
                            offset = i * width - (0.8/2) + (width/2)
                            ax3_q.bar(x + offset, y_vals, width, label=f"{d_date}", color=colors[i%len(colors)])
                            
                        team_avg_q_dist = df_q['Total Distance (m)'].mean()
                        if pd.notna(team_avg_q_dist):
                            ax3_q.axhline(team_avg_q_dist, color='blue', linestyle='--', label='Period Daily Avg')
                            
                        ax3_q.set_xticks(x)
                        ax3_q.set_xticklabels(players)
                        ax3_q.margins(x=0.05)
                        
                        ax3_q.set_ylim(0, get_dist_ymax(df_q['Total Distance (m)'].max()))
                        ax3_q.legend(loc='upper right', fontsize='small')
                        st.pyplot(fig3_q)
                        st.download_button(label="📥 下載圖表 (每日負荷)", data=get_img_buffer(fig3_q), file_name=f"Daily_Load_{selected_date}.png", mime="image/png")
                    else:
                        st.info("💡 此週期內找不到每日的 Total 資料來進行拆解。")
                        
                else:
                    st.subheader("3️⃣ 單節/分段 體能維持率")
                    is_training = 'training' in selected_session.lower()
                    if is_training:
                        quarter_sessions = [s for s in sessions_for_date if 'training' in str(s).lower() and str(s).split()[-1].isdigit()]
                    else:
                        quarter_sessions = [s for s in sessions_for_date if 'training' not in str(s).lower() and str(s).split()[-1].isdigit()]

                    quarter_sessions = sorted(quarter_sessions)

                    if len(quarter_sessions) > 0:
                        df_q = df[df['Session'].isin(quarter_sessions)]
                        players = sorted(df_q['Player'].unique())
                        fig3_q, ax3_q = plt.subplots(figsize=(6, 4))
                        x = np.arange(len(players))
                        width = 0.8 / len(quarter_sessions)
                        colors = ['#6fa8dc', '#f6b26b', '#93c47d', '#ffd966']
                        
                        for i, q_sess in enumerate(quarter_sessions):
                            q_data = df_q[df_q['Session'] == q_sess]
                            y_vals = [q_data[q_data['Player'] == p]['Total Distance (m)'].max() if not q_data[q_data['Player'] == p].empty else 0 for p in players]
                            offset = i * width - (0.8/2) + (width/2)
                            ax3_q.bar(x + offset, y_vals, width, label=f"{q_sess}", color=colors[i%len(colors)])
                            
                        team_avg_q_dist = df_q['Total Distance (m)'].mean()
                        if pd.notna(team_avg_q_dist):
                            ax3_q.axhline(team_avg_q_dist, color='blue', linestyle='--', label='Session Avg')
                            
                        ax3_q.set_xticks(x)
                        ax3_q.set_xticklabels(players)
                        ax3_q.margins(x=0.05)
                        
                        ax3_q.set_ylim(0, get_dist_ymax(df_q['Total Distance (m)'].max()))
                        
                        ax3_q.legend(loc='upper right', fontsize='small')
                        st.pyplot(fig3_q)
                        st.download_button(label="📥 下載圖表 (體能維持)", data=get_img_buffer(fig3_q), file_name=f"Fitness_Maintenance_{selected_date}.png", mime="image/png")
                    else:
                        st.info("💡 此時段無單節資料或為單日加總資料。")

            st.write("<br>", unsafe_allow_html=True)
            st.subheader("4️⃣ 爆發力象限圖 (Plotly 互動版)")
            spacer1, col_center, spacer2 = st.columns([1, 4, 1])
            with col_center:
                # 🌟 將 X 軸數據換成 Sprint Distance
                x_data = df_plot['Sprint Distance (m)']
                y_data = df_plot['Top Speed (m/s)']
                session_avg_sprint = x_data.mean()
                session_avg_top = y_data.mean()
                
                plot_text = df_plot['Player'] + " (" + df_plot['Position'] + ")" if 'Position' in df_plot.columns else df_plot['Player']
                
                fig4 = go.Figure()
                fig4.add_trace(go.Scatter(
                    x=x_data, y=y_data, mode='markers+text',
                    text=plot_text, textposition="top center",
                    marker=dict(color='#e06666', size=12, line=dict(width=1, color='white')), name='Players',
                    hovertemplate='<b>%{text}</b><br>Sprint Dist: %{x:.1f} m<br>Top Speed: %{y:.1f} m/s<extra></extra>'
                ))

                if pd.notna(session_avg_sprint) and pd.notna(session_avg_top):
                    fig4.add_trace(go.Scatter(
                        x=[session_avg_sprint], y=[session_avg_top], mode='markers',
                        marker=dict(color='blue', symbol='cross', size=14), name='Session Avg',
                        hovertemplate='<b>團隊平均</b><br>Sprint Dist: %{x:.1f} m<br>Top Speed: %{y:.1f} m/s<extra></extra>'
                    ))
                    fig4.add_vline(x=session_avg_sprint, line_dash="dash", line_color="blue", opacity=0.3)
                    fig4.add_hline(y=session_avg_top, line_dash="dash", line_color="blue", opacity=0.3)

                fig4.add_trace(go.Scatter(
                    x=[default_baseline_data['sprint_dist']], y=[default_baseline_data['top_spd']], mode='markers',
                    marker=dict(color='gold', symbol='star', size=18, line=dict(width=1, color='darkgray')), name=default_baseline_name,
                    hovertemplate=f'<b>{default_baseline_name}</b><br>Sprint Dist: %{{x:.1f}} m<br>Top Speed: %{{y:.1f}} m/s<extra></extra>'
                ))

                max_sprint_plot = max(x_data.max() if not x_data.empty else 0, default_baseline_data['sprint_dist'])
                max_top_plot = max(y_data.max() if not y_data.empty else 0, default_baseline_data['top_spd'])
                
                # 🌟 X軸使用更適合小單位的動態倍率
                x_max_plot = max(5, (int(max_sprint_plot) // 2 + 1) * 2) 
                y_max_plot = max(10, (int(max_top_plot) // 2 + 1) * 2)

                fig4.update_layout(
                    xaxis_title='<b>Sprint Distance (m)</b>', yaxis_title='<b>Top Speed (m/s)</b>',
                    xaxis=dict(range=[0, x_max_plot]), yaxis=dict(range=[0, y_max_plot]),
                    margin=dict(l=20, r=20, t=30, b=20), hovermode='closest',
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                )
                
                st.plotly_chart(
                    fig4, 
                    use_container_width=True, 
                    config={
                        'editable': True,  
                        'displayModeBar': True,
                        'toImageButtonOptions': {'format': 'png', 'filename': 'Womens_Sixes_Scatter', 'scale': 3} 
                    }
                )
        else:
            st.warning("此時段沒有數據喔！")

    # ==========================================
    # 模式二：個人專屬報告 (Player Profile - Total Focus)
    # ==========================================
    elif page_mode == "👤 個人報告 (Player Profile)":
        st.title("🥍 女網六人制 GPS 戰情室 - 個人報告")
        st.sidebar.header("👤 個人報告設定")
        
        all_players = sorted(df['Player'].unique().tolist())
        selected_player = st.sidebar.selectbox("🏃 選擇選手：", all_players)
        
        player_sessions = df[df['Player'] == selected_player]['Session'].dropna().unique().tolist()
        all_sessions = df['Session'].dropna().unique().tolist()
        
        custom_session_names = [f"{name} Total" for name in custom_and_auto_names]
        
        for name in reversed(custom_session_names):
            if name in player_sessions:
                player_sessions.remove(name)
                player_sessions.insert(0, name)
            if name in all_sessions:
                all_sessions.remove(name)
                all_sessions.insert(0, name)
        
        if not player_sessions:
            st.warning(f"💡 找不到 {selected_player} 的任何數據。")
        else:
            if 'Position' in df.columns:
                raw_pos = str(df[df['Player'] == selected_player]['Position'].iloc[0])
                pos_display = f"(註冊位置: {raw_pos} | 基準對標: {default_baseline_name})"
            else:
                pos_display = f"(基準對標: {default_baseline_name})"
                
            st.write("---")
            st.subheader(f"🛡️ {selected_player} {pos_display} - 個人表現分析")

            col_radar, col_bar = st.columns([1, 1.5])

            with col_radar:
                st.markdown(f"##### 📍 六角雷達圖：對標團隊平均")
                radar_session = st.selectbox("📅 選擇雷達圖檢視事件：", player_sessions, index=0)
                
                team_radar_df = df[df['Session'] == radar_session]
                team_mean = team_radar_df[['Total Distance (m)', 'Avg Speed (m/min)', 'Top Speed (m/s)', 'Sprint Distance (m)']].mean()
                team_std = team_radar_df[['Total Distance (m)', 'Avg Speed (m/min)', 'Top Speed (m/s)', 'Sprint Distance (m)']].std().replace(0, 1).fillna(1)
                
                player_radar = df[(df['Player'] == selected_player) & (df['Session'] == radar_session)].iloc[0]

                # 🌟 雷達圖指標更新為 Sprint Distance
                categories = ['Total Distance', 'Average Speed', 'Max Speed', 'Sprint Distance']
                N = len(categories)
                
                def calc_z(col):
                    if pd.isna(player_radar[col]) or pd.isna(team_mean[col]): return 0
                    z = (player_radar[col] - team_mean[col]) / team_std[col]
                    return np.clip(z, -2, 2)
                    
                p_dist = calc_z('Total Distance (m)')
                p_avg_spd = calc_z('Avg Speed (m/min)')
                p_top_spd = calc_z('Top Speed (m/s)')
                p_sprint = calc_z('Sprint Distance (m)')
                
                player_ratios = [p_dist, p_avg_spd, p_top_spd, p_sprint]
                player_ratios += player_ratios[:1] 
                team_ratios = [0, 0, 0, 0, 0] 
                
                angles = [n / float(N) * 2 * np.pi for n in range(N)]
                angles += angles[:1]

                fig_r, ax_r = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
                ax_r.set_theta_offset(np.pi / 2)
                ax_r.set_theta_direction(-1)
                ax_r.set_xticks(angles[:-1])
                ax_r.set_xticklabels(categories, fontsize=12, fontweight='bold')
                
                ax_r.set_ylim(-2, 2)
                ax_r.set_yticks([-2, -1, 0, 1, 2])
                ax_r.set_yticklabels(['-2', '-1', '0', '1', '2'], color="grey", size=9, alpha=0.7)
                
                ax_r.plot(angles, team_ratios, linewidth=2, linestyle='dashed', color='#e06666', label=f'{radar_session} Team Avg (0)')
                ax_r.fill(angles, team_ratios, color='#e06666', alpha=0.1)
                ax_r.plot(angles, player_ratios, linewidth=2.5, color='#4a86e8', label=f'{selected_player}')
                ax_r.fill(angles, player_ratios, color='#4a86e8', alpha=0.3)
                ax_r.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1))
                st.pyplot(fig_r)
                st.download_button(label="📥 下載雷達圖", data=get_img_buffer(fig_r), file_name=f"{selected_player}_Radar.png", mime="image/png")

            with col_bar:
                st.markdown("##### 📈 歷史進步軌跡")
                compare_mode = st.radio("📊 選擇比較模式：", ["雙期比較 (2個數據)", "三期比較 (3個數據)"], horizontal=True)
                
                baseline_options = [default_baseline_name] + all_sessions
                
                if compare_mode == "雙期比較 (2個數據)":
                    col_b1, col_b2 = st.columns(2)
                    with col_b1: 
                        player_selected_session = st.selectbox("📅 當前檢視事件：", player_sessions)
                    with col_b2:
                        selected_baseline1 = st.selectbox("📉 比較基準：", baseline_options)
                    selected_baseline2 = None
                else:
                    col_b1, col_b2, col_b3 = st.columns(3)
                    with col_b1: 
                        player_selected_session = st.selectbox("📅 當前檢視事件：", player_sessions)
                    with col_b2:
                        selected_baseline1 = st.selectbox("📉 比較基準 1：", baseline_options)
                    with col_b3:
                        default_b2_idx = 1 if len(baseline_options) > 1 else 0
                        selected_baseline2 = st.selectbox("📉 比較基準 2：", baseline_options, index=default_b2_idx)

                player_current_bar = df[(df['Player'] == selected_player) & (df['Session'] == player_selected_session)].iloc[0]
                
                def get_baseline_data(b_name):
                    if b_name == default_baseline_name:
                        target = default_baseline_data
                        return {
                            'Total Distance (m)': target['dist'],
                            'Avg Speed (m/min)': target['avg_spd'],
                            'Top Speed (m/s)': target['top_spd'],
                            'Sprint Distance (m)': target['sprint_dist']
                        }, "Sixes Avg"
                    else:
                        past_data = df[(df['Player'] == selected_player) & (df['Session'] == b_name)]
                        if not past_data.empty:
                            return past_data[['Total Distance (m)', 'Avg Speed (m/min)', 'Top Speed (m/s)', 'Sprint Distance (m)']].mean(), b_name
                        else:
                            return None, b_name

                b1_data, b1_label = get_baseline_data(selected_baseline1)
                b2_data, b2_label = None, None
                if selected_baseline2:
                    b2_data, b2_label = get_baseline_data(selected_baseline2)

                warnings = []
                if b1_data is None: warnings.append(f"💡 貼心提醒：{selected_player} 在 {selected_baseline1} 剛好沒有紀錄。")
                if selected_baseline2 and b2_data is None: warnings.append(f"💡 貼心提醒：{selected_player} 在 {selected_baseline2} 剛好沒有紀錄。")
                for w in warnings: st.info(w)

                fig_b, axes = plt.subplots(1, 4, figsize=(10, 4))
                
                # 🌟 長條圖第四項改為 Sprint Distance
                metrics = [
                    ('Total Distance', 'Total Distance (m)', ['#f4cccc', '#ea9999', '#e06666']),
                    ('Average Speed', 'Avg Speed (m/min)', ['#ead1dc', '#d5a6bd', '#c27ba0']),
                    ('Max Speed', 'Top Speed (m/s)', ['#fff2cc', '#fce5cd', '#f6b26b']),
                    ('Sprint Distance (m)', 'Sprint Distance (m)', ['#eff5e1', '#d9ead3', '#93c47d'])
                ]
                
                def format_label(text):
                    if text == "Sixes Avg": return text
                    return text.replace(' ', '\n', 1)

                for i, (title, col_name, color_palette) in enumerate(metrics):
                    plot_labels = []
                    plot_vals = []
                    plot_colors = []
                    
                    # 🌟 移除了原本計算 HSD Ratio 的乘 100 邏輯，因為 Sprint 也是直接呈現距離 (m)
                    if b2_data is not None:
                        plot_labels.append(format_label(b2_label))
                        v = b2_data[col_name] if pd.notna(b2_data[col_name]) else 0
                        plot_vals.append(v)
                        plot_colors.append(color_palette[0]) 
                        
                    if b1_data is not None:
                        plot_labels.append(format_label(b1_label))
                        v = b1_data[col_name] if pd.notna(b1_data[col_name]) else 0
                        plot_vals.append(v)
                        plot_colors.append(color_palette[1] if b2_data is not None else color_palette[0])
                        
                    plot_labels.append(format_label(player_selected_session))
                    v = player_current_bar[col_name] if pd.notna(player_current_bar[col_name]) else 0
                    plot_vals.append(v)
                    plot_colors.append(color_palette[2]) 
                    
                    bars = axes[i].bar(plot_labels, plot_vals, color=plot_colors, width=0.6)
                    axes[i].set_title(title, fontweight='bold', fontsize=11)
                    axes[i].spines['top'].set_visible(False)
                    axes[i].spines['right'].set_visible(False)
                    
                    if plot_vals:
                        max_y = max(plot_vals)
                        if pd.notna(max_y) and max_y >= 0:
                            if 'Total Distance' in title:
                                axes[i].set_ylim(0, get_dist_ymax(max_y))
                            elif 'Average Speed' in title:
                                y_max = max(100, (int(max_y) // 20 + 1) * 20)
                                axes[i].set_ylim(0, y_max)
                            elif 'Max Speed' in title:
                                y_max = max(10, (int(max_y) // 2 + 1) * 2)
                                axes[i].set_ylim(0, y_max)
                            elif 'Sprint Distance' in title:
                                # 🌟 為 Sprint Distance 量身打造的小刻度動態邊界
                                y_max = max(5, (int(max_y) // 5 + 1) * 5)
                                axes[i].set_ylim(0, y_max)
                    
                    for bar in bars:
                        yval = bar.get_height()
                        if pd.notna(yval) and yval > 0:
                            format_str = f"{int(yval)}" if 'Distance' in title and 'Sprint' not in title else f"{yval:.1f}"
                            axes[i].text(bar.get_x() + bar.get_width()/2, yval + (yval*0.02), format_str, ha='center', va='bottom', fontweight='bold', fontsize=10)

                plt.tight_layout()
                st.pyplot(fig_b)
                st.download_button(label="📥 下載長條圖 (歷史進步軌跡)", data=get_img_buffer(fig_b), file_name=f"{selected_player}_History.png", mime="image/png")