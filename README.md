# FBX to USDC Converter

[Русский](README.md) | [English](README.en.md)

Автоматизирует ручной пайплайн превращения анимации персонажа из FBX в
самодостаточный `.usdc` (Houdini, Solaris). Собирает всю цепочку одной кнопкой:
FBX Character Import в SOP → три нулла (rest / capture / animated) → SOP Import
UsdSkel Character в Solaris → USD ROP, — и опционально сразу пишет файл.

Тул обрабатывает частый случай, когда меш+скелет и анимация лежат в **двух
разных FBX** на одном скелете: оба файла указываются на одной ноде FBX
Character Import (`fbxfile` + `animfbxfile`), которая склеивает их сама — без
Bone Deform / Joint Deform вручную.

## Установка

1. Скачай последнюю версию из [последнего релиза](https://github.com/himakarov/fbx-to-usdc/releases/latest).
2. Найди папку пользовательских настроек Houdini и папку `packages` внутри неё
(создай `packages`, если её ещё нет):
  - Windows: `C:/Users/<name>/Documents/houdini22.0/packages/`
  - macOS: `~/Library/Preferences/houdini/22.0/packages/`
  - Linux: `~/houdini22.0/packages/` (подставь свою версию)
3. Распакуй zip прямо в папку `packages`, чтобы получилось:

```
houdini22.0/
└── packages/
    ├── fbx_to_usdc.json
    └── FbxToUsdcConverter/
        ├── VERSION
        ├── python/
        ├── config/
        └── scripts/
```

Переименовывать ничего не нужно — архив уже разложен правильно.

4. Перезапусти Houdini. На полке **CGA Tools** появится кнопка **FBX>USDC**.

## Использование

1. Нажми **FBX>USDC** на полке.
2. Укажи **Mesh FBX** — меш со скелетом (rest). Даёт rest-геометрию и capture-позу.
3. Укажи **Animation FBX** — клип на том же скелете. Можно оставить пустым, если
анимация уже внутри меш-FBX.
4. Путь выходного `.usdc` автозаполняется из имени аним-FBX (то есть по имени
шота) — правится вручную.
5. Задай **FPS / Start / End** вручную или нажми **Detect from Animation FBX** —
кнопка читает реальный диапазон кадров клипа (те же номера, что видит аниматор)
и подставляет родной FPS файла.
6. Оставь **Write USDC now** выключенным, чтобы только собрать и осмотреть сеть,
или включи — чтобы собрать и записать за один проход.

Дополнительные опции на вкладке Single:

- **Shift animation to start at frame 0** — если аниматор прислал клип, который
начинается с произвольного кадра (например 235), сдвигает его к нулю.
- **Create Reference node** — после записи создаёт в `/stage` Reference-ноду,
читающую готовый `.usdc` обратно в сцену.
- **Chain onto the previous reference** — подключает новую Reference-ноду к
предыдущей, собирая один общий стейдж вместо россыпи отдельных нод.
- **Clean up build nodes after export** — удаляет черновую сеть после записи,
оставляя только Reference-ноду.

## Batch Convert

Вкладка для конвертации пачки клипов за один проход. Таблица строк
(меш, анимация, выходной файл) заполняется двумя кнопками:

- **Add Pair...** — разные персонажи с разными анимациями, по строке за раз.
- **Add Animations for One Mesh...** — один персонаж и много анимаций: меш
выбирается один раз, дальше мультивыбор анимационных файлов.

Общие настройки (FPS / диапазон / запись / референсы / очистка) применяются ко
всем строкам. Отдельно есть **Auto-detect range per row** — тогда поля
Start/End игнорируются, и для каждой строки определяется её собственный
диапазон; если FPS файла отличается от указанного в поле, в отчёте появится
пометка. Отчёт показывает по каждой строке диапазон, путь и результат.

Тул строит сеть с нуля (вариант A — уникальные имена нод при каждом запуске):

```
/obj/<geo>
  fbxcharacterimport   (оба файла: fbxfile + animfbxfile)
    ├─ выход 0 → REST_GEO       (Null)
    ├─ выход 1 → CAPTURE_POSE   (Null)
    └─ выход 2 → ANIMATED_POSE  (Null)

/stage
  usdskel_import   (animposepath / restgeopath / captureposepath)
        │
  usd_rop → <name>.usdc
```

## Save Style и самодостаточный файл

USD ROP пишет со стилем **Flatten Stage (Collapse All Sublayers and
References)**. Это принципиально: ветка `convert_to_agent` внутри SOP Import
UsdSkel Character подтягивает вспомогательный слой (`OUT_STATIC`) через
**reference**, поэтому более мягкий «Flatten Implicit Layers» его не втягивает и
Houdini ругается сообщением *«Layer saved to a location generated from a node
path»*. Полный flatten стейджа схлопывает references тоже — на выходе один
переносимый `.usdc` без внешних слоёв.

Поведение настраивается в `config/settings.json` (`flatten_stage`,
`usd_save_style`).

## Настройки

`config/settings.json` хранит имена нод, primitive-пути, дефолтные FPS/диапазон,
паттерн выходного пути и save-style. Правь его, а не код. Если файл отсутствует
или сломан — используются встроенные значения по умолчанию.

## Обновление

Кнопка **Check for updates** тянет последнюю версию с GitHub. Если есть более
новая версия, она скачивается и перезаписывает локальные файлы. После обновления
перезапусти Houdini. Кнопка **Changelog** показывает, что изменилось.
