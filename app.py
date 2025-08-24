def inject_custom_css():
    st.markdown("""
    <style>
        /* General Background */
        .stApp {
            background: #f7f9fc;
            font-family: "Inter", "Segoe UI", Roboto, sans-serif;
        }

        /* Sidebar */
        section[data-testid="stSidebar"] {
            background-color: #1a1d2d;
            padding: 1rem;
        }
        section[data-testid="stSidebar"] h1, 
        section[data-testid="stSidebar"] p, 
        section[data-testid="stSidebar"] label {
            color: #f0f0f0 !important;
        }
        .css-1v3fvcr { color: white !important; }

        /* Titles */
        h1, h2, h3 {
            color: #0f172a;
            font-weight: 600;
        }

        /* Input fields */
        .stTextInput > div > div > input, 
        .stTextArea textarea, 
        .stDateInput input {
            border-radius: 10px;
            border: 1px solid #d1d5db;
            padding: 10px;
        }

        /* File uploader */
        [data-testid="stFileUploader"] {
            border: 2px dashed #6366f1;
            border-radius: 12px;
            background: #eef2ff;
        }

        /* Buttons */
        button[kind="primary"] {
            background: linear-gradient(90deg, #6366f1, #3b82f6);
            color: white;
            border-radius: 10px;
            font-weight: 600;
            transition: 0.2s ease;
        }
        button[kind="primary"]:hover {
            transform: scale(1.02);
            background: linear-gradient(90deg, #4f46e5, #2563eb);
        }

        button[kind="secondary"] {
            border-radius: 10px;
            background: #f1f5f9;
            color: #111827;
        }

        /* Form boxes */
        .stForm {
            background: white;
            padding: 2rem;
            border-radius: 16px;
            box-shadow: 0 6px 16px rgba(0,0,0,0.08);
        }

        /* Signature canvas */
        canvas {
            border: 2px solid #d1d5db !important;
            border-radius: 12px;
        }
    </style>
    """, unsafe_allow_html=True)

# Call it once at the top of main()
inject_custom_css()

