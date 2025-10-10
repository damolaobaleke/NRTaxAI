import axios from 'axios';

export let instance

if (process.env.REACT_APP_BASE_URL != null){
    instance = axios.create({ baseURL: process.env.REACT_APP_BASE_URL });
}else{
    console.error(`REACT_APP_BASE_URL is required.`)
}
