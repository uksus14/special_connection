const currentReality = document.head.dataset.reality || window.location.pathname.split('/')[1];
function shiftRealities(reality) {
    if(reality == "hacks" || currentReality == "hacks"){
        window.location.href = "/" + reality;
    }else{
        window.location.href = window.location.href.replace(`/${currentReality}/`, `/${reality}/`);
    }
}

const searchParams = new URLSearchParams(window.location.search);
if (currentReality != 'time-machine'){
    searchParams.delete("time");
    window.history.pushState({}, "", "?" + searchParams.toString());
}
if (currentReality != 'hacks'){
    document.getElementById(`${currentReality}-shift`).style.display = 'none';
} 
const back = () => window.location.href = `/${currentReality}/?time=${searchParams.get('time')}`;


window.addEventListener("keyup", event => {
    if (event.key == "Escape") {
        [...document.getElementsByClassName('popup')].forEach(popup => {
            popup.style.display = 'none';
            popIsUp = false;
        });
    }
})
function enterAct(el, func){
    el.addEventListener("keypress", event => {
        if (event.key === "Enter") {
            event.preventDefault();
            func();
        }
    });
}

let markdownName = document.getElementById('markdown-name');
document.addEventListener('DOMContentLoaded', () => {
    markdownName = document.getElementById('markdown-name');
    if(markdownName)enterAct(markdownName, addMarkdown);
    [...document.getElementsByClassName('popup')].forEach(el => {
        el.onclick = (ev) => {
            if (ev.target === el){
                el.style.display = 'none';
                popIsUp = false;
            }
        };
    });
});
function addMarkdown() {
    if (!markdownName.value) return null;
    fetch(`/current/put?title=${encodeURIComponent(markdownName.value)}`, {
        method: 'PUT',
        headers: { 'X-CSRFToken': window.csrf_token }
    }).then(response => response.json()).then(({url}) => window.location.href = url);
}
function restore(index) {
    fetch(`/editor/${index}`, {
        method: 'PUT',
        headers: { 'X-CSRFToken': window.csrf_token }
    }).then(response => response.json()).then(({url}) => window.location.href = url);
}

const timefoptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    hour12: true,
};
function formatDatetime(date = Date.now()){
    const stampFormatter = new Intl.DateTimeFormat('en-US', timefoptions);
    return stampFormatter.format(date)
        .replace('AM', 'a.m.')
        .replace('PM', 'p.m.')
        .replace(/^(\w{3})(?=\s)/, '$1.');
}
function renderCards(markdowns){
    for(let markdown of markdowns) {
        if(markdown.classList.contains('inactive-card'))continue;
        const url = new URL(markdown.parentElement.href, window.location.origin);
        url.searchParams.set('raw', 'true');
        fetch(url.toString(), {
            method: 'GET',
            headers: { 'X-CSRFToken': window.csrf_token }
        }).then(response => response.text()).then(content => {
            if(content) markdown.getElementsByClassName('preview')[0].innerHTML = content;
        })
    }
}

function renderMarkdown(){
    const main = document.getElementById('main');
    renderSearch = new URLSearchParams(window.location.search);
    renderSearch.set("render", "true");
    return fetch(`${window.location.pathname}?${renderSearch.toString()}`, {
        method: 'GET',
        headers: { 'X-CSRFToken': window.csrf_token }
    }).then(response => response.text()).then(content => {
        main.innerHTML = content;
        [...main.getElementsByTagName("script")].forEach(oldScript => {
            const newScript = document.createElement("script");
            newScript.textContent = oldScript.textContent;
            document.body.appendChild(newScript);
            oldScript.remove();
        });
    });
}