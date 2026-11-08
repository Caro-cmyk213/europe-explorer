
### Teil 1: Pakete importieren ###############################################
# Die App läuft als eigenes Programm und kennt die Imports des Notebooks nicht.
import json
import os

import pandas as pd
import plotly.express as px
import streamlit as st


### Teil 2: Funktionen, die von den Seiten verwendet werden ##################
ORDNER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'daten')   


@st.cache_data                    
def daten_laden():
    ''' Lädt alle Dateien, die das Notebook in 3.5.1 exportiert hat. '''
    d = {name: pd.read_csv(f'{ORDNER}/{name}.csv') for name in ['wirtschaft', 'innovation_jahr', 'laender']}
    with open(f'{ORDNER}/geo_laender.geojson', encoding='utf-8') as f:
        d['geo_laender'] = json.load(f)
    with open(f'{ORDNER}/info.json', encoding='utf-8') as f:
        d['info'] = json.load(f)

    # Länderübersicht: Durchschnitte aus Teil 1 (Inflation, Arbeitslosigkeit) zu den Kennzahlen aus Teil 2/3 ergänzen
    von, bis = d['info']['zeitraum']
    w = d['wirtschaft'][d['wirtschaft']['year'].between(von, bis)]
    mittel = w.groupby('country_code', as_index=False)[['inflation_hicp_pct', 'unemployment_pct']].mean()
    d['uebersicht'] = d['laender'].merge(mittel, on='country_code', how='left')
    return d


def plot_karte(df, spalte, titel, skala):
    ''' Europakarte der Länder (wie europakarte() im Notebook, Abschnitt 3.2.2). '''
    fig = px.choropleth_map(df, geojson=d['geo_laender'], locations='country_code',            
                            featureidkey='properties.CNTR_ID', color=spalte, hover_name='name_de',
                            color_continuous_scale=skala, zoom=2.6, center={'lat': 54, 'lon': 15},
                            opacity=0.8, map_style='carto-positron', title=titel, labels={spalte: ''},
                            hover_data={'country_code': False, spalte: ':.2f'})
    fig.update_layout(height=560, margin=dict(l=0, r=0, t=40, b=0))
    st.plotly_chart(fig)


def plot_zeitreihe(df, spalte, titel, krisen):
    ''' Liniendiagramm je Land mit markierten Krisenphasen. '''
    fig = px.line(df, x='year', y=spalte, color='name_de', markers=True, title=titel,
                  labels={'year': 'Jahr', spalte: '', 'name_de': 'Land'})
    for krise, (von, bis) in krisen.items():
        fig.add_vrect(x0=von - 0.5, x1=bis + 0.5, fillcolor='red', opacity=0.08, line_width=0,
                      annotation_text=krise, annotation_position='top left')
    fig.update_layout(height=420)
    st.plotly_chart(fig)


def plot_rang(df, titel):
    ''' Rang eines Landes je Jahr, Rang 1 oben (wie in Abschnitt 3.3.4). '''
    fig = px.line(df, x='year', y='rang', color='kennzahl', markers=True, title=titel,
                  labels={'year': 'Jahr', 'rang': 'Rang (1 = bester)', 'kennzahl': ''})
    fig.update_yaxes(autorange='reversed')
    fig.update_layout(height=380)
    st.plotly_chart(fig)


def plot_ranking(df, spalte, titel, farben):
    ''' Liegendes Balkendiagramm als Rangliste, Farbe = UN-Region. '''
    fig = px.bar(df, x=spalte, y='name_de', color='region_un', orientation='h', title=titel,
                 color_discrete_map=farben, labels={spalte: 'Zukunfts-Score (0–100)', 'name_de': '',
                                                     'region_un': 'UN-Region'})
    fig.update_yaxes(categoryorder='total ascending')
    fig.update_layout(height=550)
    st.plotly_chart(fig)


### Teil 3: Eine Funktion je Seite ###########################################

###### Seite 1: Europa im Überblick (Wirtschaft und Innovation)
def seite_uebersicht():
    info, ueb = d['info'], d['uebersicht']
    von, bis = info['zeitraum']
    st.title('🌍 Europe Explorer')
    st.subheader('Europa im Überblick: Wirtschaft und Innovation')
    st.markdown(f"Durchschnittswerte {von}–{bis} (Patente 2000–2017) für {len(ueb)} EU-Länder. "
                f"Wirtschaftsdaten aus Teil 1, Innovationsdaten aus Teil 2, Karte und Gruppen aus Teil 3. "
                f"Quelle: Eurostat, Stand {info['stand']}.")

    # a) Karte der gewählten Kennzahl
    kennzahlen = {'Ø reales BIP-Wachstum (%)': ('wachstum', 'RdYlGn'),
                  'Ø Inflation (%)': ('inflation_hicp_pct', 'OrRd'),
                  'Ø Arbeitslosenquote (%)': ('unemployment_pct', 'OrRd'),
                  'Ø FuE-Ausgaben (% des BIP)': ('fue', 'YlGnBu'),
                  'Ø Patente je Mio. Einwohner (2000–2017)': ('patente', 'YlGnBu')}
    name = st.selectbox('Kennzahl auswählen', list(kennzahlen))
    spalte, skala = kennzahlen[name]
    plot_karte(ueb, spalte, name if spalte == 'patente' else f'{name}, {von}–{bis}', skala)
    st.markdown('**Muster:** Innovation ist im Norden und Westen am höchsten, Wachstum im Osten. '
                'Die Länder mit den höchsten Forschungsausgaben wachsen meist unterdurchschnittlich.')

    # b) Länder über ein Suchfeld filtern
    st.subheader('Länder suchen')
    suche = st.text_input('Ländername eingeben (leer = alle Länder)', value='').lower()
    treffer = ueb[ueb['name_de'].str.lower().str.contains(suche)]
    tabelle = (treffer[['name_de', 'region_un', 'wachstum', 'inflation_hicp_pct', 'unemployment_pct',
                        'fue', 'patente', 'gruppe']]
               .rename(columns={'name_de': 'Land', 'region_un': 'UN-Region', 'wachstum': 'BIP-Wachstum %',
                                'inflation_hicp_pct': 'Inflation %', 'unemployment_pct': 'Arbeitslosigkeit %',
                                'fue': 'FuE % BIP', 'patente': 'Patente je Mio.', 'gruppe': 'Ländergruppe'})
               .sort_values('Land').round(2))
    st.dataframe(tabelle, hide_index=True)


###### Seite 2: Deutschland im Vergleich
def seite_deutschland():
    land, w, j, info = d['laender'], d['wirtschaft'], d['innovation_jahr'], d['info']
    st.subheader('🇩🇪 Deutschland im Vergleich')

    # a) Hauptland wählen (Deutschland voreingestellt)
    namen = sorted(land['name_de'].tolist())
    name = st.selectbox('Land auswählen', namen, index=namen.index('Deutschland'))
    z = land[land['name_de'] == name].iloc[0]
    st.markdown(f"**{name}** · Ø FuE-Ausgaben **{z['fue']:.2f} %** des BIP (Rang {int(z['rang_fue'])}) · "
                f"Ø BIP-Wachstum **{z['wachstum']:.2f} %** (Rang {int(z['rang_wachstum'])}) · {z['gruppe']}")

    # b) Vergleichsländer per Häkchen auswählen
    st.markdown('**Vergleichsländer auswählen:**')
    auswahl = land.loc[land['name_de'] != name, ['name_de', 'region_un']].sort_values('name_de').reset_index(drop=True)
    auswahl['Vergleich'] = auswahl['name_de'].isin(['Frankreich', 'Polen', 'Schweden'])
    editor = st.data_editor(auswahl, hide_index=True, height=210, disabled=['name_de', 'region_un'])
    laender = [name] + editor.loc[editor['Vergleich'] == True, 'name_de'].to_list()

    st.subheader('Wirtschaftswachstum und Krisen (Teil 1)')
    plot_zeitreihe(w[w['name_de'].isin(laender)].dropna(subset=['gdp_growth_pct']), 'gdp_growth_pct',
                   'Reales BIP-Wachstum (%) – rot markiert: Krisenphasen', info['krisen'])

    st.subheader('Forschung und Entwicklung (Teil 2)')
    plot_zeitreihe(j[j['name_de'].isin(laender)].dropna(subset=['rd_pct_gdp']), 'rd_pct_gdp',
                   'FuE-Ausgaben (% des BIP)', info['krisen'])

    st.subheader(f'Rang von {name} in Europa (Teil 3)')
    zeilen = []
    for spalte, text in [('rd_pct_gdp', 'FuE-Ausgaben'), ('gdp_growth_pct', 'BIP-Wachstum')]:
        t = j.dropna(subset=[spalte]).copy()
        t['rang'] = t.groupby('year')[spalte].rank(ascending=False, method='min')
        zeilen.append(t.loc[t['name_de'] == name, ['year', 'rang']].assign(kennzahl=text))
    plot_rang(pd.concat(zeilen), f'Rang von {name} je Jahr (1 = bester Wert)')

    st.subheader('Einbruch in den Krisen')
    zeilen = []
    for krise, (von, bis) in info['krisen'].items():
        t = w[w['name_de'].isin(laender) & w['year'].between(von, bis)]
        zeilen.append(t.groupby('name_de')['gdp_growth_pct'].min().rename(f'{krise} ({von}–{bis})'))
    st.dataframe(pd.concat(zeilen, axis=1).round(1))
    st.caption('Schlechtestes reales BIP-Wachstum (%) des jeweiligen Landes innerhalb der Krisenphase.')


###### Seite 3: Extra – Zukunfts-Score mit eigener Gewichtung
def seite_score():
    land = d['laender']
    st.subheader('🏆 Zukunfts-Score: eigene Gewichtung einstellen')
    st.markdown('Wer führt die Zukunft an? Das hängt davon ab, was man unter „Zukunft“ versteht. '
                'Mit den Reglern lässt sich festlegen, wie stark Forschung, Patente und Wachstum zählen.')
    regler = st.columns(3)                                              
    gewichte = {'fue': regler[0].slider('Gewicht FuE-Ausgaben', 0, 100, 33),    
                'patente': regler[1].slider('Gewicht Patente', 0, 100, 33),
                'wachstum': regler[2].slider('Gewicht Wachstum', 0, 100, 34)}
    if sum(gewichte.values()) == 0:
        st.markdown('*Mindestens ein Gewicht muss größer als 0 sein.*')
        return

    # Berechnung wie in Abschnitt 3.4: Min-Max-Skalierung, gewichteter Mittelwert
    teile = pd.DataFrame({k: (land[k] - land[k].min()) / (land[k].max() - land[k].min()) for k in gewichte})
    g = pd.Series(gewichte, dtype=float)
    score = land[['name_de', 'region_un']].copy()
    score['score'] = 100 * teile.mul(g).sum(axis=1, min_count=1) / teile.notna().mul(g).sum(axis=1)
    score['rang'] = score['score'].rank(ascending=False, method='min')
    de = score[score['name_de'] == 'Deutschland'].iloc[0]
    st.markdown(f"Mit dieser Gewichtung liegt **Deutschland auf Rang {int(de['rang'])}** von {len(score)} "
                f"(Score {de['score']:.1f}).")
    plot_ranking(score.nlargest(15, 'score'), 'score', 'Top 15 nach Zukunfts-Score', d['info']['region_farben'])
    st.caption('Jede Kennzahl wird auf 0 (schwächstes) bis 1 (stärkstes Land) skaliert und gewichtet gemittelt. '
               'Nur das Verhältnis der Gewichte zählt.')


### Teil 4: Hauptprogramm ####################################################

###### a. Daten laden und Grundeinstellungen
st.set_page_config(page_title='Europe Explorer', page_icon='🌍', layout='wide')   
d = daten_laden()
px.defaults.template = 'plotly_white'

###### b. Navigation in der Seitenleiste 
st.sidebar.title('Navigation')
seite = st.sidebar.radio('Gehe zu', ['Europa im Überblick', 'Deutschland im Vergleich', 'Extra: Zukunfts-Score'])
st.sidebar.markdown('---')
st.sidebar.caption('Projekt „Python for Data Science“ · Teil 1–3 · Daten: Eurostat')

###### c. Je nach Auswahl die passende Seitenfunktion ausführen
if seite == 'Europa im Überblick':
    seite_uebersicht()
elif seite == 'Deutschland im Vergleich':
    seite_deutschland()
elif seite == 'Extra: Zukunfts-Score':
    seite_score()
