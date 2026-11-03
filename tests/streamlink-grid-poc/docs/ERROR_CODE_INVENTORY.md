# Literal GridError code inventory

Generated from literal `GridError("...")` calls under `soop_grid/*.py` at commit `ac16c6b21093ea4159c96d9695ebcbab1a37b7c7`. Dynamic error-code construction is not represented. The table records source locations and a coarse handling class; the caller control flow remains authoritative.

Found 280 literal call sites, 212 distinct codes.

| Error code | Handling class | Source locations |
|---|---|---|
| `aac_configuration_changed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:201, soop_grid/media.py:452, soop_grid/mpegts.py:234, soop_grid/mpegts.py:242 |
| `aac_pes_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/mpegts.py:182, soop_grid/mpegts.py:204 |
| `aac_profile_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:450, soop_grid/mpegts.py:236 |
| `aac_raw_data_blocks_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:454, soop_grid/mpegts.py:238 |
| `account_credentials_required` | Authorization/access/session terminal; no media-recovery retry | soop_grid/bootstrap.py:101 |
| `account_input_invalid` | Authorization/access/session terminal; no media-recovery retry | soop_grid/auth.py:130, soop_grid/bootstrap.py:87 |
| `account_login_denied_or_verification_required` | Authorization/access/session terminal; no media-recovery retry | soop_grid/auth.py:150 |
| `account_session_unconfirmed` | Authorization/access/session terminal; no media-recovery retry | soop_grid/auth.py:154 |
| `adts_channel_config_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/aac.py:118 |
| `adts_chunk_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/aac.py:93 |
| `adts_crc_layout_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/aac.py:138 |
| `adts_frame_length_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/aac.py:131 |
| `adts_frame_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/aac.py:104 |
| `adts_header_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/aac.py:106, soop_grid/aac.py:109 |
| `adts_input_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/aac.py:91, soop_grid/aac.py:96 |
| `adts_profile_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/aac.py:115 |
| `adts_sample_rate_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/aac.py:112 |
| `adult_check_unconfirmed` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:192 |
| `audio_chunk_clock_mismatch` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:471 |
| `audio_prefix_unconfirmed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:71 |
| `audio_preroll_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/media.py:527 |
| `audio_timestamp_cumulative_drift` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:493 |
| `audio_timestamp_regression` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:459, soop_grid/media.py:464, soop_grid/mpegts.py:244 |
| `bootstrap_schema_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:253 |
| `broadcast_number_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/bootstrap.py:164, soop_grid/bootstrap.py:71 |
| `broadcast_target_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:67 |
| `buffer_backpressure_timeout` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/stream.py:111 |
| `buffer_output_unit_invalid` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/stream.py:82 |
| `cache_frame_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/parent.py:264, soop_grid/parent.py:331 |
| `cache_request_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/parent.py:329 |
| `capture_byte_limit_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/bootstrap.py:78 |
| `capture_close_failed` | Diagnostic/capture resource failure; requested output fails; Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/media.py:720 |
| `capture_deadline_reached` | Capture deadline/stop, not media corruption; Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/parent.py:299, soop_grid/protocol.py:129 |
| `capture_duration_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/bootstrap.py:76 |
| `capture_limits_invalid` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/parent.py:127, soop_grid/parent.py:125 |
| `center_access_denied` | Authorization/access/session terminal; no media-recovery retry | soop_grid/center.py:141 |
| `center_body_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/protocol.py:52 |
| `center_discovery_sequence_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/center.py:179, soop_grid/center.py:189 |
| `center_init_unexpected` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/center.py:148 |
| `center_quality_not_honored` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/center.py:195 |
| `center_session_missing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/center.py:156 |
| `certificate_length_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/center.py:44 |
| `channel_live_number_unavailable` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:161 |
| `control_checksum_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/protocol.py:95 |
| `diagnostic_thread_start_failed` | Diagnostic/capture resource failure; requested output fails | soop_grid/diagnostics.py:509 |
| `diagnostic_write_failed` | Diagnostic/capture resource failure; requested output fails | soop_grid/diagnostics.py:255 |
| `first_party_http_failed` | Terminal application validation; owning caller is authoritative | soop_grid/auth.py:86 |
| `first_party_http_rejected` | Terminal application validation; owning caller is authoritative | soop_grid/auth.py:76 |
| `first_party_json_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/auth.py:110 |
| `gateway_body_limit` | Authorization/access/session terminal; no media-recovery retry; Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/protocol.py:46 |
| `gateway_certificate_denied` | Authorization/access/session terminal; no media-recovery retry | soop_grid/gateway.py:92 |
| `gateway_certificate_fields_invalid` | Authorization/access/session terminal; no media-recovery retry | soop_grid/gateway.py:54 |
| `gateway_cookie_missing_or_invalid` | Authorization/access/session terminal; no media-recovery retry | soop_grid/bootstrap.py:239, soop_grid/bootstrap.py:214 |
| `gateway_login_denied` | Authorization/access/session terminal; no media-recovery retry | soop_grid/gateway.py:69 |
| `gateway_login_fields_invalid` | Authorization/access/session terminal; no media-recovery retry | soop_grid/gateway.py:26 |
| `gateway_login_response_layout` | Authorization/access/session terminal; no media-recovery retry | soop_grid/gateway.py:65 |
| `gateway_login_unterminated_field` | Authorization/access/session terminal; no media-recovery retry | soop_grid/gateway.py:67 |
| `gateway_negative_reply` | Authorization/access/session terminal; no media-recovery retry | soop_grid/protocol.py:94 |
| `gateway_ticket_missing_or_invalid` | Authorization/access/session terminal; no media-recovery retry | soop_grid/bootstrap.py:241 |
| `grid_composition_offset_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1224, soop_grid/h264clock.py:1299, soop_grid/media.py:64 |
| `grid_quality_metadata_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/bootstrap.py:43, soop_grid/media.py:218, soop_grid/quality.py:43, soop_grid/quality.py:45 |
| `grid_quality_resolution_mismatch` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:407 |
| `grid_quality_resolution_unverified` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/stream.py:49 |
| `grid_quality_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/center.py:130, soop_grid/media.py:220, soop_grid/quality.py:37 |
| `grid_video_dts_not_increasing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1212, soop_grid/h264clock.py:1215 |
| `guid_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/crypto.py:358 |
| `h264_access_unit_boundary_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1077, soop_grid/h264clock.py:987 |
| `h264_bit_depth_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:199 |
| `h264_chroma_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:191 |
| `h264_codec_configuration_changed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1021, soop_grid/h264clock.py:1026, soop_grid/h264clock.py:1035, soop_grid/h264clock.py:1040 |
| `h264_dimensions_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:234, soop_grid/h264clock.py:273 |
| `h264_dpb_bound_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:262 |
| `h264_emulation_prevention_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:89, soop_grid/h264clock.py:85 |
| `h264_field_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:33 |
| `h264_frame_num_gap` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:738 |
| `h264_frame_num_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1142 |
| `h264_golomb_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:44 |

| `h264_header_truncated` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:26 |
| `h264_hrd_initial_delay_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:427 |
| `h264_hrd_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:107 |
| `h264_hrd_low_delay_timing_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1075 |
| `h264_hrd_parameters_ambiguous` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:454 |
| `h264_idr_picture_id_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:763 |
| `h264_idr_reference_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:747 |
| `h264_interlaced_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:237 |
| `h264_level_dpb_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:160 |
| `h264_memory_management_operation_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:708 |
| `h264_memory_management_operation_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:709 |
| `h264_multiple_pictures_per_grid_chunk` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1122 |
| `h264_nal_count_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/mpegts.py:22 |
| `h264_nal_header_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:79 |
| `h264_parameter_set_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:174, soop_grid/h264clock.py:554 |
| `h264_parameter_set_missing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1067 |
| `h264_parameter_set_trailing_bits_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:66, soop_grid/h264clock.py:71, soop_grid/h264clock.py:69 |
| `h264_pic_struct_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:462 |
| `h264_picture_order_conflict` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1313, soop_grid/h264clock.py:1238 |
| `h264_poc2_nonreference_sequence_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1192 |
| `h264_poc_cycle_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:225 |
| `h264_poc_fields_missing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:893 |
| `h264_poc_mode_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:209 |
| `h264_poc_width_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:218 |
| `h264_pps_chroma_qp_offset_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:537, soop_grid/h264clock.py:641 |
| `h264_pps_id_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:558 |
| `h264_pps_qp_offset_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:532, soop_grid/h264clock.py:639 |
| `h264_pps_scaling_layout_mismatch` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1016 |
| `h264_pps_scaling_layout_unconfirmed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:604 |
| `h264_profile_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:180 |
| `h264_ref_list_modification_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:659 |
| `h264_ref_list_modification_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:661 |
| `h264_reference_count_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:260 |
| `h264_reference_count_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:230, soop_grid/h264clock.py:565, soop_grid/h264clock.py:790 |
| `h264_reorder_bound_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:358, soop_grid/h264clock.py:1236 |
| `h264_reorder_bound_unconfirmed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:151 |
| `h264_reorder_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:266 |
| `h264_reserved_sps_bits_nonzero` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:182 |
| `h264_sei_after_vcl` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:983 |
| `h264_sei_buffering_period_missing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1089 |
| `h264_sei_buffering_period_order_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:514, soop_grid/h264clock.py:411 |
| `h264_sei_buffering_period_unexpected` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:415 |
| `h264_sei_message_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:387, soop_grid/h264clock.py:498 |
| `h264_sei_parameter_set_mismatch` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:413, soop_grid/h264clock.py:418 |
| `h264_sei_payload_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:523 |
| `h264_sei_timing_duplicate` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:449, soop_grid/h264clock.py:1082 |
| `h264_sei_timing_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:406 |
| `h264_sei_trailing_bits_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:486, soop_grid/h264clock.py:516 |
| `h264_sei_truncated` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:401, soop_grid/h264clock.py:512, soop_grid/h264clock.py:395, soop_grid/h264clock.py:506 |
| `h264_separate_colour_plane_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:195 |
| `h264_slice_count_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:1055 |
| `h264_slice_groups_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:562 |
| `h264_slice_nal_type_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:744 |
| `h264_slice_parameter_set_mismatch` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:756 |
| `h264_slice_type_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:752 |
| `h264_sps_id_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:185 |
| `h264_start_boundary_unavailable` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:876, soop_grid/h264clock.py:970 |
| `h264_switching_slice_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:779 |
| `h264_vcl_missing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1053 |
| `h264_vcl_partition_or_extension_unsupported` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:1043 |
| `h264_vui_timing_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:340 |
| `h264_weighted_bipred_reserved` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/h264clock.py:569 |
| `http_deadline_reached` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/auth.py:68 |
| `http_destination_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/auth.py:47, soop_grid/auth.py:133, soop_grid/bootstrap.py:89 |
| `http_response_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/auth.py:82 |
| `incoming_body_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/protocol.py:108 |
| `invalid_server_endpoint` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:142, soop_grid/protocol.py:32 |
| `issued_certificate_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/center.py:60 |
| `issued_seed_required` | Terminal application validation; owning caller is authoritative | soop_grid/center.py:72 |
| `issued_ticket_required` | Terminal application validation; owning caller is authoritative | soop_grid/center.py:94 |
| `join_field_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/center.py:102, soop_grid/center.py:119 |
| `join_quality_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/center.py:104 |
| `live_metadata_denied_or_offline` | Authorization/access/session terminal; no media-recovery retry | soop_grid/bootstrap.py:180 |
| `live_target_changed` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:185 |
| `media_dts_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/mpegts.py:173 |
| `media_dts_not_monotonic` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/mpegts.py:177 |
| `media_header_short` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:46 |
| `media_kind_unconfirmed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:60 |
| `media_layout_unconfirmed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:57 |
| `media_pcr_gap_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/mpegts.py:121 |
| `media_pcr_not_increasing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/mpegts.py:119 |
| `media_pts_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/mpegts.py:171, soop_grid/mpegts.py:240 |
| `media_pts_dts_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/mpegts.py:175 |
| `media_startup_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/media.py:369 |
| `media_timestamp_bounds` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/h264clock.py:860, soop_grid/h264clock.py:962, soop_grid/h264clock.py:1301, soop_grid/media.py:66, soop_grid/mpegts.py:284 |
| `media_track_coverage_incomplete` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/stream.py:52 |
| `media_track_coverage_unverified` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/stream.py:54 |
| `network_read_failed` | Parent retry candidate (finite outage budget only); Auto HLS fallback candidate only before Grid output | soop_grid/protocol.py:74 |
| `network_read_timeout` | Parent retry candidate (finite outage budget only); Auto HLS fallback candidate only before Grid output; Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/protocol.py:67, soop_grid/protocol.py:72 |
| `network_write_failed` | Parent retry candidate (finite outage budget only); Auto HLS fallback candidate only before Grid output | soop_grid/protocol.py:166 |
| `no_playable_grid_audio` | Terminal application validation; owning caller is authoritative | soop_grid/stream.py:47 |
| `no_playable_grid_video` | Terminal application validation; owning caller is authoritative | soop_grid/stream.py:45 |
| `no_usable_server_parent` | Auto HLS fallback candidate only before Grid output | soop_grid/parent.py:76 |
| `parent_access_denied` | Authorization/access/session terminal; no media-recovery retry | soop_grid/parent.py:316 |
| `parent_body_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/protocol.py:58 |
| `parent_discovery_missing` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/center.py:205 |
| `parent_header_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/protocol.py:87 |
| `parent_list_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/parent.py:79 |
| `parent_list_length` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/parent.py:34 |
| `parent_list_short` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/parent.py:31 |
| `parent_list_trailing_data` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/parent.py:36 |
| `parent_media_stalled` | Parent retry candidate (finite outage budget only); Auto HLS fallback candidate only before Grid output | soop_grid/parent.py:291, soop_grid/parent.py:427, soop_grid/parent.py:304 |
| `parent_packet_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/parent.py:314 |
| `parent_rediscovery_empty` | Auto HLS fallback candidate only before Grid output | soop_grid/parent.py:212 |
| `parent_retry_limit` | Auto HLS fallback candidate only before Grid output; Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/parent.py:220 |
| `password_state_unknown` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:187 |
| `peer_closed_or_truncated` | Parent retry candidate (finite outage budget only); Auto HLS fallback candidate only before Grid output | soop_grid/protocol.py:76 |
| `private_capture_create_failed` | Diagnostic/capture resource failure; requested output fails | soop_grid/media.py:287 |
| `public_policy_restricted_or_unknown` | Authorization/access/session terminal; no media-recovery retry | soop_grid/bootstrap.py:199 |
| `public_watch_access_denied` | Authorization/access/session terminal; no media-recovery retry | soop_grid/bootstrap.py:224 |
| `public_watch_schema_invalid` | Authorization/access/session terminal; no media-recovery retry | soop_grid/bootstrap.py:226 |
| `reader_shutdown_timeout` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/stream.py:460 |
| `reader_timeout` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/stream.py:381, soop_grid/stream.py:431 |
| `receiver_closed` | Terminal application validation; owning caller is authoritative | soop_grid/auth.py:60, soop_grid/auth.py:66 |
| `scoped_cookie_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/auth.py:119 |
| `sps_chroma` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:130 |
| `sps_cycle_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/media.py:155 |
| `sps_dimensions_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:174 |
| `sps_golomb_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/media.py:102 |
| `sps_poc_invalid` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:159 |
| `sps_truncated` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:90 |
| `startup_already_committed` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/startup.py:103 |
| `startup_byte_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/startup.py:154, soop_grid/startup.py:203 |
| `startup_capture_unsupported` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/bootstrap.py:58 |
| `startup_configuration_invalid` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/bootstrap.py:56 |
| `startup_staging_limit` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/startup.py:86 |
| `startup_timeout` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/startup.py:152, soop_grid/startup.py:198, soop_grid/startup.py:261, soop_grid/stream.py:212 |
| `startup_unverified` | Configuration/resource/lifecycle bound; terminal except explicit deadline stop | soop_grid/startup.py:238 |
| `stream_password_encoding_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:105, soop_grid/center.py:62 |
| `stream_password_state_mismatch` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:190 |
| `tcp_connect_failed` | Parent retry candidate (finite outage budget only); Auto HLS fallback candidate only before Grid output | soop_grid/protocol.py:151 |
| `user_agent_invalid` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:95 |
| `video_prefix_unconfirmed` | Protocol/media validation; fail closed, no retry/fallback | soop_grid/media.py:69 |
| `watch_target_changed` | Terminal application validation; owning caller is authoritative | soop_grid/bootstrap.py:229 |
