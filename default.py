﻿#!/usr/bin/python
# -*- coding: utf-8 -*-


import locale
locale.setlocale(locale.LC_ALL, '')

import datetime
import os
import pickle
from datetime import datetime
from urlparse import urlparse
import urllib2

import dateutil.parser
from dateutil.tz import tzlocal, tzoffset

import BeautifulSoup
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
from simpleplugin import Plugin


ID_PLUGIN = 'plugin.video.mflive'

__addon__ = xbmcaddon.Addon(id=ID_PLUGIN)
__path__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__media__ = os.path.join( __path__,'resources', 'media')


SITE = __addon__.getSetting('url_site')



def dbg_log(line):
    if __addon__.getSetting('is_debug') == 'true':
        xbmc.log('%s [v.%s]: %s' % (ID_PLUGIN, __version__, line))


def _http_get(url):
    try:
        req = urllib2.Request(url=url)
        req.add_header('User-Agent',
                       'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 5.1; Trident/4.0; Mozilla/4.0'
                       ' (compatible; MSIE 6.0; Windows NT 5.1; SV1) ; .NET CLR 1.1.4322; .NET CLR 2.0.50727; '
                       '.NET CLR 3.0.4506.2152; .NET CLR 3.5.30729; .NET4.0C)')
        resp = urllib2.urlopen(req)
        http = resp.read()
        resp.close()
        return http
    except Exception, e:
        print('[%s]: GET EXCEPT [%s]' % (ID_PLUGIN, e), 4)
        print url


LEAGUES = []

with open(os.path.join(__path__, 'leagues.pickle'), 'rb') as f:
    LEAGUES = pickle.load(f)


plugin = Plugin()


def _get_selected_leagues():
    sl = __addon__.getSetting('selected_leagues')
    if not sl:
        sl = '0'
    return map(lambda x: int(x), sl.split(','))


@plugin.action()
def root():
    matches = get_matches()
    select_item = [{'label': '[COLOR FF0084FF][B]ВЫБРАТЬ ТУРНИРЫ[/B][/COLOR]',
                    'url': plugin.get_url(action='select_matches')}, ]
    # return plugin.create_listing(select_item + matches, content='tvseries',
    #                              view_mode=55, sort_methods={'sortMethod': xbmcplugin.SORT_METHOD_NONE, 'label2Mask': '% J'})
    return select_item + matches


@plugin.action()
def select_matches(params):

    selected_leagues = _get_selected_leagues()

    result = xbmcgui.Dialog().multiselect(
        u'Выбор турнира', LEAGUES, preselect=selected_leagues)

    if not result is None:
        if not len(result):
            result.append(0)
        __addon__.setSetting('selected_leagues', ','.join(str(x)
                                                          for x in result))
        cache_file = os.path.join(xbmc.translatePath(
            __addon__.getAddonInfo('profile')), '__cache__.pcl')
        if os.path.exists(cache_file):
            os.remove(cache_file)
        root()


@plugin.cached(20)
def get_matches():
    selected_leagues = _get_selected_leagues()
    html = _http_get(SITE)
    matches = []
    urls = set()
    tzs = int(__addon__.getSetting('time_zone_site'))
#    tzl = 2

    now_date = datetime.now().replace(tzinfo=tzlocal())
    soup = BeautifulSoup.BeautifulSoup(html)
    days = soup.findAll('div', {'class': 'rewievs_tab1'})

    for match_html in days:

        url = match_html.contents[1]['href']

        if url in urls:
            continue
        dbg_log(url)
        urls.add(url)

        tbody = match_html.findAll('tbody')[1]
        image = tbody.contents[1].contents[1].contents[1]['src']
        icon = SITE + image
        label = tbody.contents[1].contents[3].text
        league = tbody.contents[1].contents[1].contents[1]['title']
        dbg_log(image)
        dbg_log(label.encode('utf8'))
        dbg_log(league.encode('utf8'))
        if not selected_leagues or not selected_leagues[0]:
            dbg_log('Фильтра нет')
        else:
            try:
                if not LEAGUES.index(league) in selected_leagues:
                    continue
            except ValueError:
                dbg_log('Добавим - %s - в список' % league.encode('utf8'))
                LEAGUES.append(league)
                index = LEAGUES.index(league)
                with open(os.path.join(__path__, 'leagues.pickle'), 'wt') as f:
                    f.write(pickle.dumps(LEAGUES, 0))
                sl = _get_selected_leagues()
                sl.append(index)
                __addon__.setSetting('selected_leagues',
                                     ','.join(str(x) for x in sl))

       
        ic = os.path.join(__media__, league + '.png')
        
        if os.path.exists(ic.encode('utf-8')):
            icon = ic

        dts = tbody.contents[3].contents[1].contents[0].contents[1]['data-time']
        dt = dateutil.parser.parse(dts)
        tz = tzoffset(None, tzs * 3600)
        dt = dt.replace(tzinfo=tz)
        date_time = dt.astimezone(tzlocal())
        dbg_log(date_time)

        before_time = int((date_time - now_date).total_seconds()/60)

        if before_time < -110:
            status = 'FF999999'
        elif before_time > 0:
            status = 'FFFFFFFF'
        else:
            status = 'FFFF0000'

        label = u'[COLOR %s]%s[/COLOR] - [B]%s[/B]  (%s)' % (
            status, date_time.strftime('%H:%M').decode('utf8'), label, league)
        plot = u'[B][UPPERCASE]%s[/B][/UPPERCASE]\n%s\n' % (
            date_time.strftime('%d %b %Y').decode('utf8'), league)
        
        matches.append({'label': label,
                        'thumb': icon,
                        #'fanart': icon,
                        'info': {'video': {'title': plot, 'plot': plot}},
                        'icon': icon,
                        'url': plugin.get_url(action='get_links', url=url, image=icon)})
        dbg_log(matches[-1])

    return matches


@plugin.cached(10)
@plugin.action()
def get_links(params):

    dbg_log(params['url'])

    html = _http_get(params['url'])
    matches = []
    icon1 = ''
    command1 = ''
    icon2 = ''
    command2 = ''

    soup = BeautifulSoup.BeautifulSoup(html)

    stream_full_table_soup = soup.find(
        'table', {'class': 'stream-full-table stream-full-table1'})

    span_soup = stream_full_table_soup.findAll('span')

    #title = stream_full_table_soup.find('td', {'class': 'stream-full5'}).contents[1].text
    # dbg_log(title.encode('utf8'))

    stream_full_soup = stream_full_table_soup.find(
        'td', {'class': 'stream-full'})
    if stream_full_soup:
        icon1 = stream_full_soup.contents[0]['src']
        command1 = stream_full_soup.contents[0]['title']

    stream_full2_soup = stream_full_table_soup.find(
        'td', {'class': 'stream-full2'})
    if stream_full2_soup:
        icon2 = stream_full2_soup.contents[0]['src']
        command2 = stream_full2_soup.contents[0]['title']

    dbg_log(icon1.encode('utf8'))
    dbg_log(command1.encode('utf8'))
    dbg_log(icon2.encode('utf8'))
    dbg_log(command2.encode('utf8'))

    plot = u'%s\n%s\n%s - %s' % (span_soup[0].text,
                                 span_soup[1].text, command1, command2)

    list_link_stream_soup = soup.findAll(
        'table', {'class': 'list-link-stream'})

    #xbmcgui.Dialog().notification(u'Проверка ссылок:', command1 + ' - ' + command2, xbmcgui.NOTIFICATION_INFO, 5000)

    if list_link_stream_soup:

        links_font_soup = list_link_stream_soup[0].findAll(
            'span', {'class': 'links-font'})

        for link_soup in links_font_soup:
            bit_rate = link_soup.text.split('-')[1].strip()
            href = link_soup.contents[0]['href']

            urlprs = urlparse(href)

            if urlprs.scheme == 'acestream':
                icon = os.path.join(__media__, 'ace.png')
            elif urlprs.scheme == 'sop':
                icon = os.path.join(__media__, 'sop.png')
            else:
                icon = os.path.join(__media__, 'http.png')

            matches.append({'label': '%s - %s' % (urlprs.scheme, bit_rate),
                            'info': {'video': {'title': command1 + ' - ' + command2, 'plot': plot}},
                            'thumb': icon,
                            'icon': os.path.join(__media__, 'm.png'),
                            #  'fanart': os.path.join(__path__, 'fanart.jpg'),
                            'art': {'clearart': os.path.join(__media__, 'm.png')},
                            'url': plugin.get_url(action='play', url=href),
                            'is_playable': True})
            dbg_log(matches[-1])

    iframe_soup = soup.findAll('iframe', {'rel': "nofollow"})
    for s in iframe_soup:
        html_frame = _http_get(s['src'])
        if html_frame:
            ilink = html_frame.find('var videoLink')
            if ilink != -1:
                i1 = html_frame.find('\'', ilink)
                i2 = html_frame.find('\'', i1 + 1)
                href = html_frame[i1+1:i2]
                urlprs = urlparse(href)
                matches.append({'label': u'%s - прямая ссылка на видео...' % urlprs.scheme,
                                'info': {'video': {'title': command1 + ' - ' + command2, 'plot': plot}},
                                'thumb': os.path.join(__media__, 'http.png'),
                                'icon': os.path.join(__media__, 'http.png'),
                                # 'fanart': os.path.join(__path__, 'fanart.jpg'),
                                'url': plugin.get_url(action='play', url=href),
                                'is_playable': True})
                dbg_log(matches[-1])

    if not matches:
        matches.append({'label': u'Ссылок на трансляции нет, возможно появятся позже!',
                        'info': {'video': {'title': '', 'plot': ''}},
                        # 'thumb': icon2,
                        #'icon': params['image'],
                        'art': {'clearart': ''},
                        'url': plugin.get_url(action='play', url='https://www.ixbt.com/multimedia/video-methodology/camcorders-and-others/htc-one-x-avc-baseline@l3.2-1280x720-variable-fps-aac-2ch.mp4'),
                        'is_playable': True})
    return matches


@plugin.action()
def play(params):
    path = ''
    item = 0
    url = urlparse(params['url'])
    if url.scheme == 'acestream':
        if __addon__.getSetting('is_default_play') == 'true':
            item = int(__addon__.getSetting('default_ace'))
        else:
            dialog = xbmcgui.Dialog()
            item = dialog.contextmenu(
                ['ACESTREAM %s [%s]' % ('hls' if __addon__.getSetting(
                    'is_hls1') == 'true' else '', __addon__.getSetting('ipace1')),
                 'ACESTREAM %s [%s]' % ('hls' if __addon__.getSetting(
                     'is_hls2') == 'true' else '', __addon__.getSetting('ipace2')),
                 'HTTPAceProxy [%s]' % __addon__.getSetting('ipproxy'), 'Add-on TAM [127.0.0.1]'])
            if item == -1:
                return

        cid = url.netloc

        if item == 0:
            path = 'http://%s:6878/ace/%s?id=%s' % (
                __addon__.getSetting('ipace1'), 'manifest.m3u8' if __addon__.getSetting(
                    'is_hls1') == 'true' else 'getstream', cid)
        elif item == 1:
            path = 'http://%s:6878/ace/%s?id=%s' % (
                __addon__.getSetting('ipace2'), 'manifest.m3u8' if __addon__.getSetting(
                    'is_hls2') == 'true' else 'getstream', cid)
        elif item == 2:
            path = "http://%s:8000/pid/%s/stream.mp4" % (
                __addon__.getSetting('ipproxy'), cid)
        elif item == 3:
            path = "plugin://plugin.video.tam/?mode=play&url=%s&engine=ace_proxy" % params['url']
    elif url.scheme == 'sop':
        path = "plugin://program.plexus/?mode=2&url=" + \
            url.geturl() + "&name=Sopcast"
    else:
        path = url.geturl()

    dbg_log(path)

    return Plugin.resolve_url(path, succeeded=True)


if __name__ == '__main__':
    plugin.run()
