import streamlit as st
from superadmin import list_tenants, deactivate_tenant, delete_tenant, create_tenant
from users import list_users_by_tenant, create_user, deactivate_user, delete_user
from utils import load_language, translator

def main():
    lang = st.session_state.get("language", "de")
    texts = load_language(lang)
    t = translator(texts)

    if "user" not in st.session_state or st.session_state["user"]["role"] != "superadmin":
        st.error("Zugriff verweigert.")
        st.stop()

    st.title(t("superadmin_dashboard"))

    # Logout
    if st.button(t("logout_button")):
        st.session_state.clear()
        st.switch_page("login.py")

    st.sidebar.title("Navigation")
    action = st.sidebar.radio(
        "",
        (t("tenant_management"), t("user_management"), t("create_tenant_user"))
    )

    if action == t("tenant_management"):
        st.header(t("tenant_management"))
        tenants = list_tenants()

        if not tenants:
            st.info(t("no_tenants"))
        else:
            for tnt in tenants:
                st.markdown("---")
                st.write(f"{t('tenant_id')}: {tnt['id']}")
                st.write(f"{t('active')}: {tnt.get('active', True)}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(f"{t('deactivate')} {tnt['id']}", key=f"deact_{tnt['id']}"):
                        deactivate_tenant(tnt["id"])
                        st.rerun()
                with col2:
                    if st.button(f"{t('delete')} {tnt['id']}", key=f"del_{tnt['id']}"):
                        delete_tenant(tnt["id"])
                        st.rerun()

    elif action == t("user_management"):
        st.header(t("user_management"))
        tenant_id = st.text_input(t("tenant_id"))

        if tenant_id:
            users = list_users_by_tenant(tenant_id)
            if not users:
                st.info(t("no_users"))
            else:
                for u in users:
                    st.markdown("---")
                    st.write(f"{t('email')}: {u['email']}")
                    st.write(f"{t('active')}: {u.get('active', True)}")

                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button(f"{t('deactivate')} {u['email']}", key=f"udeact_{u['id']}"):
                            deactivate_user(u["id"])
                            st.rerun()
                    with col2:
                        if st.button(f"{t('delete')} {u['email']}", key=f"udel_{u['id']}"):
                            delete_user(u["id"])
                            st.rerun()

    elif action == t("create_tenant_user"):
        st.header(t("create_tenant_user"))

        tenant_id = st.text_input(t("tenant_id"))
        email = st.text_input(t("customer_email"))
        password = st.text_input(t("customer_password"), type="password")

        if st.button(t("create_button")):
            if not tenant_id or not email or not password:
                st.error("Bitte alle Felder ausfüllen.")
            else:
                create_tenant(tenant_id)
                create_user(email, password, "customer", tenant_id)
                st.success("Mandant + Benutzer erstellt.")

if __name__ == "__main__":
    main()
