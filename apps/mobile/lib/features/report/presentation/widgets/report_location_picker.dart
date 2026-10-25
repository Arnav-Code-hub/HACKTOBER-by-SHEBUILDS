import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:latlong2/latlong.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../../../core/config/app_config.dart';
import '../../../../core/services/location_service.dart';
import '../../../../core/theme/app_spacing.dart';
import '../../../../shared/widgets/jm_app_bar.dart';

/// Manual pinning works independently of device location permission.
class ReportLocationPicker extends StatefulWidget {
  const ReportLocationPicker({super.key, this.initialPosition});

  final ResolvedPosition? initialPosition;

  @override
  State<ReportLocationPicker> createState() => _ReportLocationPickerState();
}

class _ReportLocationPickerState extends State<ReportLocationPicker> {
  static const _districtCentre = LatLng(16.76, 77.14);
  LatLng? _selected;

  @override
  void initState() {
    super.initState();
    final initial = widget.initialPosition;
    if (initial != null) {
      _selected = LatLng(initial.latitude, initial.longitude);
    }
  }

  @override
  Widget build(BuildContext context) {
    final selected = _selected;
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: const JmAppBar.task(title: 'Choose report location'),
      body: Column(
        children: <Widget>[
          Padding(
            padding: const EdgeInsets.all(Insets.md),
            child: Text(
              'Move the map and tap the problem location to place a pin. '
              'The map starts in ${AppConfig.defaultDistrict}.',
            ),
          ),
          Expanded(
            child: FlutterMap(
              options: MapOptions(
                initialCenter: selected ?? _districtCentre,
                initialZoom: 14,
                minZoom: 4,
                maxZoom: 18,
                onTap: (_, point) => setState(() => _selected = point),
              ),
              children: <Widget>[
                TileLayer(
                  urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                  userAgentPackageName: 'in.janmaang.app',
                  maxNativeZoom: 19,
                ),
                if (selected != null)
                  MarkerLayer(
                    markers: <Marker>[
                      Marker(
                        point: selected,
                        width: 44,
                        height: 44,
                        alignment: Alignment.topCenter,
                        child: Icon(
                          Icons.location_pin,
                          size: 44,
                          color: scheme.primary,
                          semanticLabel: 'Selected report location',
                        ),
                      ),
                    ],
                  ),
                RichAttributionWidget(
                  attributions: <SourceAttribution>[
                    TextSourceAttribution(
                      'OpenStreetMap contributors',
                      onTap: () => launchUrl(
                        Uri.parse('https://www.openstreetmap.org/copyright'),
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          SafeArea(
            top: false,
            child: Padding(
              padding: const EdgeInsets.all(Insets.md),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: <Widget>[
                  Text(
                    selected == null
                        ? 'No location selected. Tap the map to choose.'
                        : '${selected.latitude.toStringAsFixed(5)}, '
                              '${selected.longitude.toStringAsFixed(5)}',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: Insets.sm),
                  FilledButton.icon(
                    onPressed: selected == null
                        ? null
                        : () {
                            Navigator.of(context).pop(
                              ResolvedPosition(
                                latitude: selected.latitude,
                                longitude: selected.longitude,
                                label:
                                    'Map pin: ${selected.latitude.toStringAsFixed(5)}, '
                                    '${selected.longitude.toStringAsFixed(5)}',
                              ),
                            );
                          },
                    icon: const Icon(Icons.check),
                    label: const Text('Use this location'),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}
