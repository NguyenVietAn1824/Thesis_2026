import json

data = {
    "models": [
        {
            "name": "provinces",
            "properties": {
                "description": "Provinces table stores province-level administrative information for Vietnam. Use this to find province names, IDs, or geographic boundaries. Contains id (example: 12), name_vi (example: Hà Nội), name_en (example: Hanoi)."
            },
            "columns": [
                {
                    "name": "id",
                    "type": "TEXT",
                    "properties": {
                        "description": "Unique identifier for each province"
                    }
                },
                {
                    "name": "name_vi",
                    "type": "TEXT",
                    "properties": {
                        "description": "Official name of the province or city in Vietnamese",
                        "example": ["Hà Nội", "Hồ Chí Minh"]
                    }
                },
                {
                    "name": "name_en",
                    "type": "TEXT",
                    "properties": {
                        "description": "Official name of the province or city in English",
                        "example": ["Hanoi", "Ho Chi Minh City"]
                    }
                },
                {
                    "name": "type_vi",
                    "type": "TEXT",
                    "properties": {
                        "description": "Administrative type in Vietnamese",
                        "example": ["Thành phố Trung ương", "Tỉnh"]
                    }
                },
                {
                    "name": "type_en",
                    "type": "TEXT",
                    "properties": {
                        "description": "Administrative type in English"
                    }
                },
                {
                    "name": "extent_minx",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box min longitude"}
                },
                {
                    "name": "extent_maxx",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box max longitude"}
                },
                {
                    "name": "extent_miny",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box min latitude"}
                },
                {
                    "name": "extent_maxy",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box max latitude"}
                }
            ]
        },
        {
            "name": "districts",
            "properties": {
                "description": "Districts table stores all district-level areas (Quận/Huyện) within provinces. Use this to find district names or IDs within a province."
            },
            "columns": [
                {
                    "name": "id",
                    "type": "TEXT",
                    "properties": {
                        "description": "Internal district identifier"
                    }
                },
                {
                    "name": "province_id",
                    "type": "TEXT",
                    "properties": {
                        "description": "Foreign key referencing provinces.id, linking the district to its parent province"
                    }
                },
                {
                    "name": "name_vi",
                    "type": "TEXT",
                    "properties": {
                        "description": "Official Vietnamese name of the district",
                        "example": ["Quận Ba Đình", "Huyện Thanh Trì"]
                    }
                },
                {
                    "name": "name_en",
                    "type": "TEXT",
                    "properties": {
                        "description": "English name of the district",
                        "example": ["Ba Dinh District"]
                    }
                },
                {
                    "name": "type_vi",
                    "type": "TEXT",
                    "properties": {
                        "description": "Administrative type in Vietnamese",
                        "example": ["Quận", "Huyện", "Thị xã"]
                    }
                },
                {
                    "name": "type_en",
                    "type": "TEXT",
                    "properties": {
                        "description": "Administrative type in English"
                    }
                },
                {
                    "name": "extent_minx",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box min longitude"}
                },
                {
                    "name": "extent_maxx",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box max longitude"}
                },
                {
                    "name": "extent_miny",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box min latitude"}
                },
                {
                    "name": "extent_maxy",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box max latitude"}
                }
            ]
        },
        {
            "name": "wards",
            "properties": {
                "description": "Wards table stores all ward/commune-level areas (Phường/Xã) within districts."
            },
            "columns": [
                {
                    "name": "id",
                    "type": "TEXT",
                    "properties": {"description": "Internal ward identifier"}
                },
                {
                    "name": "district_id",
                    "type": "TEXT",
                    "properties": {"description": "Foreign key referencing districts.id"}
                },
                {
                    "name": "province_id",
                    "type": "TEXT",
                    "properties": {"description": "Foreign key referencing provinces.id"}
                },
                {
                    "name": "name_vi",
                    "type": "TEXT",
                    "properties": {"description": "Official Vietnamese name of the ward", "example": ["Phường Tràng Tiền", "Xã Kim Chung"]}
                },
                {
                    "name": "name_en",
                    "type": "TEXT",
                    "properties": {"description": "English name of the ward"}
                },
                {
                    "name": "type_vi",
                    "type": "TEXT",
                    "properties": {"description": "Administrative type in Vietnamese", "example": ["Phường", "Xã", "Thị trấn"]}
                },
                {
                    "name": "type_en",
                    "type": "TEXT",
                    "properties": {"description": "Administrative type in English"}
                },
                {
                    "name": "extent_minx",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box min longitude"}
                },
                {
                    "name": "extent_maxx",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box max longitude"}
                },
                {
                    "name": "extent_miny",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box min latitude"}
                },
                {
                    "name": "extent_maxy",
                    "type": "FLOAT",
                    "properties": {"description": "Bounding box max latitude"}
                }
            ]
        },
        {
            "name": "air_component",
            "properties": {
                "description": "Air component table defines the types of air quality measurements tracked in the system. Contains name (example: aqi, pm25, pm10) and descriptions."
            },
            "columns": [
                {
                    "name": "id",
                    "type": "INTEGER",
                    "properties": {"description": "Auto-incremented unique identifier for each air component"}
                },
                {
                    "name": "name",
                    "type": "TEXT",
                    "properties": {
                        "description": "Short code name of the air quality component",
                        "example": ["aqi", "pm25", "o3"]
                    }
                },
                {
                    "name": "description",
                    "type": "TEXT",
                    "properties": {"description": "Human-readable description of the air component"}
                },
                {
                    "name": "created_at",
                    "type": "TIMESTAMP",
                    "properties": {"description": "Creation timestamp"}
                },
                {
                    "name": "updated_at",
                    "type": "TIMESTAMP",
                    "properties": {"description": "Update timestamp"}
                },
                {
                    "name": "deleted_at",
                    "type": "TIMESTAMP",
                    "properties": {"description": "Soft delete timestamp"}
                }
            ]
        },
        {
            "name": "distric_stats",
            "properties": {
                "description": "District stats table storing aggregated AQI and PM2.5 measurements per district. Fields like val_avg_aqi and val_avg_pm25 represent the average air quality metrics for the specific category_id. AQI levels: 0–50 Tốt (Good), 51–100 Trung bình (Moderate), 101–150 Kém (Unhealthy for sensitive), 151–200 Xấu (Unhealthy), 201–300 Rất xấu (Very unhealthy), 301+ Nguy hại (Hazardous)."
            },
            "columns": [
                {
                    "name": "id",
                    "type": "INTEGER",
                    "properties": {"description": "Auto-incremented unique identifier"}
                },
                {
                    "name": "district_id",
                    "type": "TEXT",
                    "properties": {"description": "Foreign key referencing districts.id"}
                },
                {
                    "name": "category_id",
                    "type": "TEXT",
                    "properties": {"description": "Category or time identifier for the aggregated statistics (e.g. daily or hourly grouping key)"}
                },
                {
                    "name": "num",
                    "type": "INTEGER",
                    "properties": {"description": "Count of records used in this aggregation"}
                },
                {
                    "name": "val_sum_pm25",
                    "type": "FLOAT",
                    "properties": {"description": "Sum of PM2.5 fine particulate matter concentration"}
                },
                {
                    "name": "val_avg_pm25",
                    "type": "FLOAT",
                    "properties": {"description": "Average PM2.5 fine particulate matter concentration"}
                },
                {
                    "name": "val_sum_aqi",
                    "type": "INTEGER",
                    "properties": {"description": "Sum of Air Quality Index (AQI) values"}
                },
                {
                    "name": "val_avg_aqi",
                    "type": "INTEGER",
                    "properties": {"description": "Average Air Quality Index (AQI) value"}
                }
            ]
        }
    ],
    "relationships": [
        {
            "name": "districts_to_provinces",
            "models": ["districts", "provinces"],
            "joinType": "MANY_TO_ONE",
            "condition": "districts.province_id = provinces.id"
        },
        {
            "name": "wards_to_districts",
            "models": ["wards", "districts"],
            "joinType": "MANY_TO_ONE",
            "condition": "wards.district_id = districts.id"
        },
        {
            "name": "wards_to_provinces",
            "models": ["wards", "provinces"],
            "joinType": "MANY_TO_ONE",
            "condition": "wards.province_id = provinces.id"
        },
        {
            "name": "distric_stats_to_districts",
            "models": ["distric_stats", "districts"],
            "joinType": "MANY_TO_ONE",
            "condition": "distric_stats.district_id = districts.id"
        }
    ]
}

with open("/home/nguyen-viet-an/Learn/UET/KLTN/mdl.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=4, ensure_ascii=False)
